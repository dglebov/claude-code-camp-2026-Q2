import pytest
from boukensha.backends import Ollama
from boukensha.errors import UnsupportedModelError

# Mirrors the values conftest.py builds the shared `context` fixture from. Kept literal here so
# a drift in either place fails loudly rather than silently agreeing with itself.
SYSTEM = "You are a MUD player assistant."
LOOK_RESULT = "A damp stone corridor stretches north."

MODEL = "qwen3:8b"


@pytest.fixture
def backend():
    return Ollama(model=MODEL)


def test_rejects_an_unknown_model():
    with pytest.raises(UnsupportedModelError):
        Ollama(model="llama2")


def test_model_metadata(backend):
    assert backend.context_window == 40_000
    assert backend.usage_unit == "local_compute"


def test_local_models_cost_zero_not_none(backend):
    """0.0 is truthy in Ruby, falsy in Python — see backends/base.estimate_cost."""
    assert backend.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000) == 0.0


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


def test_to_messages_identifies_tool_results_by_tool_name(backend, context):
    """OpenAI uses `tool_call_id` here; Ollama uses `tool_name`."""
    assert backend.to_messages(context.system, context.messages) == [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "What's around me?"},
        {"role": "assistant", "content": "Let me take a look around first."},
        {"role": "tool", "tool_name": "toolu_01X", "content": LOOK_RESULT},
    ]


def test_to_payload(backend, context):
    payload = backend.to_payload(context)

    assert payload == {
        "model": MODEL,
        "stream": False,
        "messages": backend.to_messages(context.system, context.messages),
        "tools": backend.to_tools(context.tools),
    }
    assert list(payload) == ["model", "stream", "messages", "tools"]


def test_max_output_tokens_is_accepted_and_ignored(backend, context):
    """Ollama takes no output cap in this step, but must answer the same call as every backend."""
    assert backend.to_payload(context, max_output_tokens=64) == backend.to_payload(context)


def test_headers_and_default_url(backend):
    assert backend.headers() == {"Content-Type": "application/json"}
    assert backend.url() == "http://localhost:11434/api/chat"


def test_custom_host_changes_the_url():
    assert Ollama(model=MODEL, host="http://box.local:9999").url() == "http://box.local:9999/api/chat"
