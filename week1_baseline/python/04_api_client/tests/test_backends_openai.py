import pytest
from boukensha.backends import OpenAI
from boukensha.errors import UnsupportedModelError

# Mirrors the values conftest.py builds the shared `context` fixture from. Kept literal here so
# a drift in either place fails loudly rather than silently agreeing with itself.
SYSTEM = "You are a MUD player assistant."
LOOK_RESULT = "A damp stone corridor stretches north."

MODEL = "gpt-5.4"


@pytest.fixture
def backend():
    return OpenAI(api_key="sk-test", model=MODEL)


def test_rejects_an_unknown_model():
    with pytest.raises(UnsupportedModelError):
        OpenAI(api_key="sk-test", model="gpt-4")


def test_model_metadata(backend):
    assert backend.context_window == 1_000_000
    assert backend.usage_unit == "tokens"
    assert backend.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000) == 17.5


def test_to_tools_wraps_in_a_function_envelope(backend, context):
    assert backend.to_tools(context.tools) == [
        {
            "type": "function",
            "function": {
                "name": "look",
                "description": "Look around the current room for details",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "move",
                "description": "Move the player in a direction",
                "parameters": {
                    "type": "object",
                    "properties": {"direction": {"type": "string", "description": "The direction to move"}},
                    "required": ["direction"],
                },
            },
        },
    ]


def test_to_messages_puts_system_first_and_uses_tool_call_id(backend, context):
    assert backend.to_messages(context.system, context.messages) == [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "What's around me?"},
        {"role": "assistant", "content": "Let me take a look around first."},
        {"role": "tool", "tool_call_id": "toolu_01X", "content": LOOK_RESULT},
    ]


def test_to_payload(backend, context):
    payload = backend.to_payload(context)

    assert payload == {
        "model": MODEL,
        "messages": backend.to_messages(context.system, context.messages),
        "tools": backend.to_tools(context.tools),
        "max_completion_tokens": 1024,
    }
    assert list(payload) == ["model", "messages", "tools", "max_completion_tokens"]


def test_to_payload_honours_max_output_tokens(backend, context):
    assert backend.to_payload(context, max_output_tokens=64)["max_completion_tokens"] == 64


def test_headers_and_url(backend):
    assert backend.headers() == {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-test",
    }
    assert backend.url() == "https://api.openai.com/v1/chat/completions"


def test_empty_context_still_carries_the_system_message(backend, empty_context):
    payload = backend.to_payload(empty_context)

    assert payload["tools"] == []
    assert payload["messages"] == [{"role": "system", "content": SYSTEM}]
