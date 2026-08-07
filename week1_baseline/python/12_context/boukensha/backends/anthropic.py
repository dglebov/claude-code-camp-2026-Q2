"""Port of `ruby/11_tui/lib/boukensha/backends/anthropic.rb`.

Talks to https://api.anthropic.com/v1/messages. The system prompt is a top-level field, tools use
`input_schema`, and a tool result is wrapped in a *user* message — counterintuitive, but it is how
the API models the conversation.

Prices are static tutorial data, current as of June 16, 2026 (see the Ruby README).
"""

from typing import ClassVar

from .base import Base


class Anthropic(Base):
    BASE_URL = "https://api.anthropic.com/v1/messages"
    MODELS: ClassVar[dict] = {
        "claude-haiku-4-5": {
            "context_window": 200_000,
            "cost_per_million": {"input": 1.0, "output": 5.0},
            "usage_unit": "tokens",
        },
        "claude-haiku-4-5-20251001": {
            "context_window": 200_000,
            "cost_per_million": {"input": 1.0, "output": 5.0},
            "usage_unit": "tokens",
        },
        "claude-sonnet-4-6": {
            "context_window": 1_000_000,
            "cost_per_million": {"input": 3.0, "output": 15.0},
            "usage_unit": "tokens",
        },
        "claude-opus-4-8": {
            "context_window": 1_000_000,
            "cost_per_million": {"input": 5.0, "output": 25.0},
            "usage_unit": "tokens",
        },
    }

    def __init__(self, *, api_key, model):
        self._api_key = api_key
        self._configure_model(model)

    def to_messages(self, messages):
        serialized = []
        for msg in messages:
            if msg.role == "tool_result":
                serialized.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": msg.tool_use_id,
                                "content": msg.content,
                            }
                        ],
                    }
                )
            elif msg.role == "assistant":
                serialized.append({"role": "assistant", "content": self._assistant_content(msg.content)})
            else:
                serialized.append({"role": msg.role, "content": msg.content})
        return serialized

    def to_tools(self, tools):
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": tool.parameters,
                    "required": tool.required_keys(),
                },
            }
            for tool in tools.values()
        ]

    def to_payload(self, context, max_output_tokens=1024, tools=None):
        return {
            "model": self._model,
            "system": context.system,
            "max_tokens": max_output_tokens,
            "tools": self.to_tools(context.tools) if tools is None else tools,
            "messages": self.to_messages(context.messages),
        }

    def headers(self):
        return {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
        }

    def url(self):
        return self.BASE_URL

    def parse_response(self, response):
        """Normalizes an Anthropic Messages API response into the common shape:

        {"stop_reason": "tool_use" | "end_turn",
         "content": [{"type": "text", "text": ...}
                     | {"type": "tool_use", "id": ..., "name": ..., "input": ...}]}

        New in step 12: Anthropic's `thinking` and `redacted_thinking` blocks are normalized to
        the common `reasoning` shape (see backends/base.py for the full contract), so the Agent
        can log model thinking without knowing which provider produced it.

        Ruby keys the outer dict with symbols and the inner blocks with strings (they come from
        parsed JSON); Python uses strings for both.
        """
        stop_reason = "tool_use" if response.get("stop_reason") == "tool_use" else "end_turn"
        content = [self._normalize_block(b) for b in (response.get("content") or [])]
        return {"stop_reason": stop_reason, "content": content}

    @staticmethod
    def _normalize_block(block):
        kind = block.get("type")
        if kind == "thinking":
            return {
                "type": "reasoning",
                "text": str(block.get("thinking") or ""),
                "signature": block.get("signature"),
            }
        if kind == "redacted_thinking":
            # No readable text, but the block still logs — it tells a reader "the model thought
            # here". `data` is carried as the signature so the round-trip below can restore it.
            return {
                "type": "reasoning",
                "text": "",
                "redacted": True,
                "signature": block.get("data"),
            }
        return block

    def _assistant_content(self, content):
        """Rebuild Anthropic assistant content from normalized blocks — the inverse of
        parse_response.

        Text-only turns are stored as a bare string and pass through unchanged. `reasoning` blocks
        are re-emitted as native thinking/redacted_thinking so their signatures round-trip intact:
        Anthropic rejects a replayed thinking block whose signature has been altered or dropped.
        """
        if isinstance(content, str):
            return content

        return [self._denormalize_block(b) for b in content]

    @staticmethod
    def _denormalize_block(block):
        if not isinstance(block, dict) or block.get("type") != "reasoning":
            return block

        if block.get("redacted"):
            return {"type": "redacted_thinking", "data": block.get("signature")}
        return {
            "type": "thinking",
            "thinking": str(block.get("text") or ""),
            "signature": block.get("signature"),
        }
