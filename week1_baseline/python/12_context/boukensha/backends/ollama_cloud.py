"""Port of `ruby/11_tui/lib/boukensha/backends/ollama_cloud.rb`.

Talks to https://ollama.com/api/chat with an API key. Same payload shape as local Ollama.

Public pricing is plan/usage based rather than per token, so every entry carries `None` costs and
`estimate_cost` returns `None`. `usage_level` records the tier instead.

Prices are static tutorial data, current as of June 16, 2026 (see the Ruby README).
"""

from typing import ClassVar

from .base import Base


class OllamaCloud(Base):
    BASE_URL = "https://ollama.com"
    MODELS: ClassVar[dict] = {
        "gemma4:31b-cloud": {
            "context_window": 256_000,
            "cost_per_million": {"input": None, "output": None},
            "usage_unit": "ollama_cloud_usage",
            "usage_level": "medium",
        },
        "minimax-m3:cloud": {
            "context_window": 512_000,
            "advertised_context_window": 1_000_000,
            "cost_per_million": {"input": None, "output": None},
            "usage_unit": "ollama_cloud_usage",
            "usage_level": "high",
        },
        "kimi-k2.5:cloud": {
            "context_window": 256_000,
            "cost_per_million": {"input": None, "output": None},
            "usage_unit": "ollama_cloud_usage",
            "usage_level": "high",
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
                conversation.append({"role": "tool", "tool_name": msg.tool_use_id, "content": msg.content})
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
                        "required": tool.required_keys(),
                    },
                },
            }
            for tool in tools.values()
        ]

    def to_payload(self, context, max_output_tokens=1024, tools=None):
        return {
            "model": self._model,
            "stream": False,
            "messages": self.to_messages(context.system, context.messages),
            "tools": self.to_tools(context.tools) if tools is None else tools,
        }

    def headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

    def url(self):
        return f"{self.BASE_URL}/api/chat"

    def parse_response(self, response):
        """Normalizes an Ollama chat response into the common shape.

        Ollama doesn't assign call ids, so the function name is reused as the id.
        """
        message = response.get("message") or {}
        tool_calls = message.get("tool_calls") or []

        content = []
        # Ruby guards with `thinking && !thinking.empty?` — an empty string produces no block.
        if message.get("thinking"):
            content.append({"type": "reasoning", "text": message["thinking"]})
        # Ruby guards with `content && !content.empty?`, so an empty string is skipped. Python's
        # plain truthiness test is equivalent here — unlike OpenAI's, which guards differently.
        if message.get("content"):
            content.append({"type": "text", "text": message["content"]})

        for call in tool_calls:
            function = call.get("function") or {}
            content.append(
                {
                    "type": "tool_use",
                    "id": function.get("name"),
                    "name": function.get("name"),
                    "input": function.get("arguments") or {},
                }
            )

        return {"stop_reason": "end_turn" if not tool_calls else "tool_use", "content": content}
