"""Port of `ruby/04_api_client/lib/boukensha/backends/gemini.rb`.

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
                serialized.append({"role": "model", "parts": [{"text": msg.content}]})
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
                            "required": list(tool.parameters),
                        },
                    }
                    for tool in tools.values()
                ]
            }
        ]

    def to_payload(self, context, max_output_tokens=1024):
        return {
            "systemInstruction": {"parts": [{"text": context.system}]},
            "contents": self.to_messages(context.messages),
            "tools": self.to_tools(context.tools),
            "generationConfig": {"maxOutputTokens": max_output_tokens},
        }

    def headers(self):
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

    def url(self):
        return f"{self.BASE_URL}/{self._model}:generateContent"
