"""Port of `ruby/11_tui/lib/boukensha/backends/gemini.rb`.

Talks to https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent — the
only backend that puts the model in the URL. Messages are `contents` with `parts`, the assistant
role is called `model`, and tool results are a `functionResponse` part on a user message.

Prices are static tutorial data, current as of June 16, 2026 (see the Ruby README).
"""

from typing import ClassVar

from .base import Base


class Gemini(Base):
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    MODELS: ClassVar[dict] = {
        "gemini-3.5-flash": {
            "context_window": 1_048_576,
            "cost_per_million": {"input": 1.5, "output": 9.0},
            "usage_unit": "tokens",
        },
        "gemini-3.1-flash-lite": {
            "context_window": 1_048_576,
            "cost_per_million": {"input": 0.25, "output": 1.5},
            "usage_unit": "tokens",
        },
        "gemini-2.5-pro": {
            "context_window": 1_048_576,
            "cost_per_million": {"input": 1.25, "output": 10.0},
            "usage_unit": "tokens",
        },
        "gemini-2.5-flash": {
            "context_window": 1_048_576,
            "cost_per_million": {"input": 0.30, "output": 2.50},
            "usage_unit": "tokens",
        },
        "gemini-2.5-flash-lite": {
            "context_window": 1_048_576,
            "cost_per_million": {"input": 0.10, "output": 0.40},
            "usage_unit": "tokens",
        },
    }

    def __init__(self, *, api_key, model):
        self._api_key = api_key
        self._configure_model(model)

    def to_messages(self, messages):
        serialized = []
        for msg in messages:
            if msg.role == "assistant":
                # Was `[{"text": msg.content}]` through step 04. The agent now stores assistant
                # turns as normalized block lists, which have to be turned back into Gemini parts.
                serialized.append({"role": "model", "parts": self._assistant_parts(msg.content)})
            elif msg.role == "tool_result":
                serialized.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": msg.tool_use_id,
                                    "response": {"content": msg.content},
                                }
                            }
                        ],
                    }
                )
            else:
                serialized.append({"role": msg.role, "parts": [{"text": msg.content}]})
        return serialized

    def to_tools(self, tools):
        if not tools:
            return []

        return [
            {
                "functionDeclarations": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": tool.parameters,
                            "required": tool.required_keys(),
                        },
                    }
                    for tool in tools.values()
                ]
            }
        ]

    def to_payload(self, context, max_output_tokens=1024, tools=None):
        return {
            "systemInstruction": {"parts": [{"text": context.system}]},
            "contents": self.to_messages(context.messages),
            "tools": self.to_tools(context.tools) if tools is None else tools,
            "generationConfig": {"maxOutputTokens": max_output_tokens},
        }

    def headers(self):
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

    def url(self):
        return f"{self.BASE_URL}/{self._model}:generateContent"

    def parse_response(self, response):
        """Normalizes a Gemini generateContent response into the common shape.

        Gemini doesn't assign call ids, so the function name is reused as the id — Gemini also
        matches a functionResponse back to its call by name.
        """
        candidates = response.get("candidates") or [{}]
        parts = (candidates[0].get("content") or {}).get("parts") or []

        content = []
        tool_used = False

        for part in parts:
            # Order matters and mirrors Ruby: functionCall first, then `thought`, then plain
            # text. A thought part also has a "text" key, so testing text first would swallow it.
            if part.get("functionCall"):
                call = part["functionCall"]
                content.append(
                    {
                        "type": "tool_use",
                        "id": call.get("name"),
                        "name": call.get("name"),
                        "input": call.get("args") or {},
                    }
                )
                tool_used = True
            elif part.get("thought"):
                content.append(
                    {
                        "type": "reasoning",
                        "text": str(part.get("text") or ""),
                        "signature": part.get("thoughtSignature"),
                    }
                )
            elif part.get("text"):
                content.append({"type": "text", "text": part["text"]})

        return {"stop_reason": "tool_use" if tool_used else "end_turn", "content": content}

    def _assistant_parts(self, content):
        """Rebuilds Gemini "model" parts from normalized content blocks — the inverse of
        parse_response. Needed because the agent stores assistant turns as block lists."""
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content

        return [
            {"functionCall": {"name": b["name"], "args": b["input"]}}
            if b.get("type") == "tool_use"
            else {"text": b.get("text")}
            for b in blocks
        ]
