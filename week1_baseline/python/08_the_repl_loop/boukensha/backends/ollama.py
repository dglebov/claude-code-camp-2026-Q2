"""Port of `ruby/08_the_repl_loop/lib/boukensha/backends/ollama.rb`.

Talks to a local `ollama serve` at http://localhost:11434/api/chat. No API key. The payload shape
matches OpenAI's apart from `stream: false` and tool results keyed by `tool_name` rather than
`tool_call_id`.

Local models cost nothing to run, so every entry prices at 0.0 — which is not the same as the
`None` used by Ollama Cloud, where pricing is plan-based rather than per token. See
`base.estimate_cost`.
"""

from typing import ClassVar

from .base import Base


class Ollama(Base):
    MODELS: ClassVar[dict] = {
        "gemma4": {
            "context_window": 128_000,
            "cost_per_million": {"input": 0.0, "output": 0.0},
            "usage_unit": "local_compute",
        },
        "gemma4:e2b": {
            "context_window": 128_000,
            "cost_per_million": {"input": 0.0, "output": 0.0},
            "usage_unit": "local_compute",
        },
        "gemma4:e4b": {
            "context_window": 128_000,
            "cost_per_million": {"input": 0.0, "output": 0.0},
            "usage_unit": "local_compute",
        },
        "gemma4:12b": {
            "context_window": 256_000,
            "cost_per_million": {"input": 0.0, "output": 0.0},
            "usage_unit": "local_compute",
        },
        "gemma4:26b": {
            "context_window": 256_000,
            "cost_per_million": {"input": 0.0, "output": 0.0},
            "usage_unit": "local_compute",
        },
        "gemma4:31b": {
            "context_window": 256_000,
            "cost_per_million": {"input": 0.0, "output": 0.0},
            "usage_unit": "local_compute",
        },
        "qwen3:30b": {
            "context_window": 256_000,
            "cost_per_million": {"input": 0.0, "output": 0.0},
            "usage_unit": "local_compute",
        },
        "qwen3:8b": {
            "context_window": 40_000,
            "cost_per_million": {"input": 0.0, "output": 0.0},
            "usage_unit": "local_compute",
        },
        "deepseek-r1:8b": {
            "context_window": 128_000,
            "cost_per_million": {"input": 0.0, "output": 0.0},
            "usage_unit": "local_compute",
        },
    }

    # Ruby writes `initialize(host: "...", model:)` — an optional keyword before a required one,
    # which Python does not allow. Both are keyword-only, so call sites are unaffected.
    def __init__(self, *, model, host="http://localhost:11434"):
        self._host = host
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
                        "required": list(tool.parameters),
                    },
                },
            }
            for tool in tools.values()
        ]

    def to_payload(self, context, max_output_tokens=1024, tools=None):
        # Ollama takes no output-token cap in this step; the argument is accepted and ignored so
        # every backend answers to the same PromptBuilder call.
        return {
            "model": self._model,
            "stream": False,
            "messages": self.to_messages(context.system, context.messages),
            "tools": self.to_tools(context.tools) if tools is None else tools,
        }

    def headers(self):
        return {"Content-Type": "application/json"}

    def url(self):
        return f"{self._host}/api/chat"

    def parse_response(self, response):
        """Normalizes an Ollama chat response into the common shape.

        Ollama doesn't assign call ids, so the function name is reused as the id.
        """
        message = response.get("message") or {}
        tool_calls = message.get("tool_calls") or []

        content = []
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
