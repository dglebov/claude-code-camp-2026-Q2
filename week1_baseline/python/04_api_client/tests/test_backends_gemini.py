import pytest
from boukensha.backends import Gemini
from boukensha.errors import UnsupportedModelError

# Mirrors the values conftest.py builds the shared `context` fixture from. Kept literal here so
# a drift in either place fails loudly rather than silently agreeing with itself.
SYSTEM = "You are a MUD player assistant."
LOOK_RESULT = "A damp stone corridor stretches north."

MODEL = "gemini-2.5-flash"


@pytest.fixture
def backend():
    return Gemini(api_key="sk-test", model=MODEL)


def test_rejects_an_unknown_model():
    with pytest.raises(UnsupportedModelError):
        Gemini(api_key="sk-test", model="gemini-1.0-pro")


def test_model_metadata(backend):
    assert backend.context_window == 1_048_576
    assert backend.usage_unit == "tokens"
    assert backend.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000) == pytest.approx(2.80)


def test_to_tools_wraps_everything_in_one_function_declarations_entry(backend, context):
    tools = backend.to_tools(context.tools)

    assert len(tools) == 1
    assert tools == [
        {
            "functionDeclarations": [
                {
                    "name": "look",
                    "description": "Look around the current room for details",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
                {
                    "name": "move",
                    "description": "Move the player in a direction",
                    "parameters": {
                        "type": "object",
                        "properties": {"direction": {"type": "string", "description": "The direction to move"}},
                        "required": ["direction"],
                    },
                },
            ]
        }
    ]


def test_to_tools_is_empty_for_no_tools(backend, empty_context):
    assert backend.to_tools(empty_context.tools) == []


def test_to_messages_renames_assistant_to_model(backend, context):
    assert backend.to_messages(context.messages) == [
        {"role": "user", "parts": [{"text": "What's around me?"}]},
        {"role": "model", "parts": [{"text": "Let me take a look around first."}]},
        {
            "role": "user",
            "parts": [{"functionResponse": {"name": "toolu_01X", "response": {"content": LOOK_RESULT}}}],
        },
    ]


def test_to_payload(backend, context):
    payload = backend.to_payload(context)

    assert payload == {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": backend.to_messages(context.messages),
        "tools": backend.to_tools(context.tools),
        "generationConfig": {"maxOutputTokens": 1024},
    }
    assert list(payload) == ["systemInstruction", "contents", "tools", "generationConfig"]


def test_to_payload_honours_max_output_tokens(backend, context):
    assert backend.to_payload(context, max_output_tokens=64)["generationConfig"] == {"maxOutputTokens": 64}


def test_headers_and_url(backend):
    assert backend.headers() == {
        "Content-Type": "application/json",
        "x-goog-api-key": "sk-test",
    }
    assert backend.url() == (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    )
