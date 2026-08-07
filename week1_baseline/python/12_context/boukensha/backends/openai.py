"""Port of `ruby/12_context/lib/boukensha/backends/openai.rb`.

Talks to https://api.openai.com/v1/responses — the **Responses API**, not chat completions.

Step 12 migrated this backend. gpt-5.x rejects `reasoning_effort` together with tools on
`/v1/chat/completions` ("Please use /v1/responses"), so the endpoint had to change, and that
changes more than the URL:

  * messages become `input` items
  * the system prompt becomes a top-level `instructions` string, not a first message
  * tool definitions are flat — no `function:` wrapper
  * tool results round-trip as `function_call_output` items matched by `call_id`, rather than a
    `{role: "tool"}` message keyed by `tool_call_id`
  * the response is an `output[]` array of typed items instead of `choices[0].message`

Prices are static tutorial data, current as of June 16, 2026 (see the Ruby README).
"""

import json
from typing import ClassVar

from .base import Base


class OpenAI(Base):
    BASE_URL = "https://api.openai.com/v1/responses"
    MODELS: ClassVar[dict] = {
        "gpt-5.5": {
            "context_window": 1_000_000,
            "cost_per_million": {"input": 5.0, "output": 30.0},
            "usage_unit": "tokens",
        },
        "gpt-5.4-mini": {
            "context_window": 400_000,
            "cost_per_million": {"input": 0.75, "output": 4.5},
            "usage_unit": "tokens",
        },
        "gpt-5.4-nano": {
            "context_window": 400_000,
            "cost_per_million": {"input": 0.2, "output": 1.25},
            "usage_unit": "tokens",
        },
    }

    def __init__(self, *, api_key, model):
        self._api_key = api_key
        self._configure_model(model)

    def to_input(self, messages):
        """Flatten the conversation into Responses `input` items.

        Ruby uses flat_map because one assistant turn can expand to several items — a text item
        plus one function_call per tool use. Python builds the list explicitly for the same reason.
        """
        items = []
        for msg in messages:
            if msg.role == "tool_result":
                items.append(
                    {
                        "type": "function_call_output",
                        "call_id": msg.tool_use_id,
                        "output": str(msg.content),
                    }
                )
            elif msg.role == "assistant":
                items.extend(self._assistant_items(msg.content))
            else:
                items.append({"role": msg.role, "content": msg.content})
        return items

    def to_tools(self, tools):
        return [
            {
                "type": "function",
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

    def to_payload(self, context, max_output_tokens=1024, tools=None):
        return {
            "model": self._model,
            "instructions": context.system,
            "input": self.to_input(context.messages),
            "tools": self.to_tools(context.tools) if tools is None else tools,
            "max_output_tokens": max_output_tokens,
            "reasoning": {"effort": "none"},
        }

    def headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

    def url(self):
        return self.BASE_URL

    def parse_response(self, response):
        """Normalize a Responses API `output[]` array into the common shape.

        Tool calls are collected first and appended after the text/reasoning blocks, matching
        Ruby: `filter_map` skips the function_call items during the first pass and they are pushed
        on afterwards, so ordering is text/reasoning first, tool_use last regardless of what the
        provider sent.
        """
        function_calls = []
        content = []

        for item in response.get("output") or []:
            kind = item.get("type")
            if kind == "reasoning":
                # The Responses API returns reasoning as a list of summary fragments.
                text = "".join(s.get("text") or "" for s in (item.get("summary") or []))
                content.append({"type": "reasoning", "text": text})
            elif kind == "message":
                text = "".join(
                    c.get("text") or ""
                    for c in (item.get("content") or [])
                    if c.get("type") == "output_text"
                )
                # Ruby's `unless text.empty?` inside filter_map drops the block entirely.
                if text:
                    content.append({"type": "text", "text": text})
            elif kind == "function_call":
                function_calls.append(item)

        for call in function_calls:
            content.append(
                {
                    "type": "tool_use",
                    "id": call.get("call_id"),
                    "name": call.get("name"),
                    "input": json.loads(call.get("arguments") or "{}"),
                }
            )

        return {
            "stop_reason": "end_turn" if not function_calls else "tool_use",
            "content": content,
        }

    # ---------- private ----------------------------------------------------

    def _assistant_items(self, content):
        """Rebuild Responses input items from normalized content blocks — the inverse of
        parse_response.

        Reasoning blocks are deliberately dropped: gpt-5.x does not need them echoed back while
        reasoning effort is "none". That is the opposite of Anthropic, which rejects a replayed
        thinking block whose signature was altered — the two providers genuinely differ here.
        """
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content

        text = "".join(b.get("text") or "" for b in blocks if b.get("type") == "text")
        items = [] if not text else [{"role": "assistant", "content": text}]

        for block in blocks:
            if block.get("type") != "tool_use":
                continue
            items.append(
                {
                    "type": "function_call",
                    "call_id": block.get("id"),
                    "name": block.get("name"),
                    "arguments": json.dumps(block.get("input")),
                }
            )
        return items
