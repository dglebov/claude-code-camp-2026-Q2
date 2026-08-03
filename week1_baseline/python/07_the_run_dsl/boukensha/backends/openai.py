"""Port of `ruby/07_the_run_dsl/lib/boukensha/backends/openai.rb`.

Talks to https://api.openai.com/v1/chat/completions. The system prompt is the first entry in the
messages array, tools are wrapped in a `function` envelope, and tool results come back as
`role: tool` keyed by `tool_call_id`.

Prices are static tutorial data, current as of June 16, 2026 (see the Ruby README).
"""

import json
from typing import ClassVar

from .base import Base


class OpenAI(Base):
    BASE_URL = "https://api.openai.com/v1/chat/completions"
    MODELS: ClassVar[dict] = {
        "gpt-5.5": {
            "context_window": 1_000_000,
            "cost_per_million": {"input": 5.0, "output": 30.0},
            "usage_unit": "tokens",
        },
        "gpt-5.4": {
            "context_window": 1_000_000,
            "cost_per_million": {"input": 2.5, "output": 15.0},
            "usage_unit": "tokens",
        },
        "gpt-5.4-mini": {
            "context_window": 400_000,
            "cost_per_million": {"input": 0.75, "output": 4.5},
            "usage_unit": "tokens",
        },
    }

    def __init__(self, *, api_key, model):
        self._api_key = api_key
        self._configure_model(model)

    def to_messages(self, system, messages):
        system_message = [{"role": "system", "content": system}]
        conversation = []
        for msg in messages:
            if msg.role == "tool_result":
                conversation.append({"role": "tool", "tool_call_id": msg.tool_use_id, "content": msg.content})
            else:
                conversation.append({"role": msg.role, "content": msg.content})
        return system_message + conversation

    def to_tools(self, tools):
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.parameters,
                        "required": list(tool.parameters),
                    },
                },
            }
            for tool in tools.values()
        ]

    def to_payload(self, context, max_output_tokens=1024, tools=None):
        return {
            "model": self._model,
            "messages": self.to_messages(context.system, context.messages),
            "tools": self.to_tools(context.tools) if tools is None else tools,
            "max_completion_tokens": max_output_tokens,
        }

    def headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

    def url(self):
        return self.BASE_URL

    def parse_response(self, response):
        """Normalizes an OpenAI chat-completions response into the common shape."""
        message = (response.get("choices") or [{}])[0].get("message") or {}
        tool_calls = message.get("tool_calls") or []

        content = []
        # Ruby guards with a bare `if message["content"]`, where "" is TRUTHY — an empty string
        # still produces a text block. `is not None` reproduces that; a plain `if` would not.
        # Note Ollama's version of this method guards differently, and deliberately so.
        if message.get("content") is not None:
            content.append({"type": "text", "text": message["content"]})

        for call in tool_calls:
            function = call.get("function") or {}
            content.append(
                {
                    "type": "tool_use",
                    "id": call.get("id"),
                    "name": function.get("name"),
                    "input": json.loads(function.get("arguments") or "{}"),
                }
            )

        # Driven by the presence of tool calls, not by the API's own finish_reason.
        return {"stop_reason": "end_turn" if not tool_calls else "tool_use", "content": content}
