import pytest
from boukensha.backends import Anthropic
from boukensha.errors import UnsupportedModelError

# Mirrors the values conftest.py builds the shared `context` fixture from. Kept literal here so
# a drift in either place fails loudly rather than silently agreeing with itself.
SYSTEM = "You are a MUD player assistant."
LOOK_RESULT = "A damp stone corridor stretches north."

MODEL = "claude-sonnet-4-6"


@pytest.fixture
def backend():
    return Anthropic(api_key="sk-test", model=MODEL)


def test_rejects_an_unknown_model():
    with pytest.raises(UnsupportedModelError):
        Anthropic(api_key="sk-test", model="claude-sonet-5")


def test_model_metadata(backend):
    assert backend.model == MODEL
    assert backend.context_window == 1_000_000
    assert backend.usage_unit == "tokens"
    assert backend.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000) == 18.0


def test_to_tools_uses_input_schema(backend, context):
    assert backend.to_tools(context.tools) == [
        {
            "name": "look",
            "description": "Look around the current room for details",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "move",
            "description": "Move the player in a direction",
            "input_schema": {
                "type": "object",
                "properties": {"direction": {"type": "string", "description": "The direction to move"}},
                "required": ["direction"],
            },
        },
    ]


def test_to_messages_wraps_tool_results_in_a_user_message(backend, context):
    assert backend.to_messages(context.messages) == [
        {"role": "user", "content": "What's around me?"},
        {"role": "assistant", "content": "Let me take a look around first."},
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "toolu_01X", "content": LOOK_RESULT}],
        },
    ]


def test_to_payload(backend, context):
    payload = backend.to_payload(context)

    assert payload == {
        "model": MODEL,
        "system": SYSTEM,
        "max_tokens": 1024,
        "tools": backend.to_tools(context.tools),
        "messages": backend.to_messages(context.messages),
    }
    assert list(payload) == ["model", "system", "max_tokens", "tools", "messages"]


def test_to_payload_honours_max_output_tokens(backend, context):
    assert backend.to_payload(context, max_output_tokens=64)["max_tokens"] == 64


def test_headers_and_url(backend):
    assert backend.headers() == {
        "Content-Type": "application/json",
        "x-api-key": "sk-test",
        "anthropic-version": "2023-06-01",
    }
    assert backend.url() == "https://api.anthropic.com/v1/messages"


def test_empty_context_serializes_to_empty_collections(backend, empty_context):
    payload = backend.to_payload(empty_context)

    assert payload["tools"] == []
    assert payload["messages"] == []


# ---------- step 05: tools override ------------------------------------------


def test_to_payload_serializes_the_contexts_tools_by_default(backend, context):
    assert backend.to_payload(context)["tools"] == backend.to_tools(context.tools)


def test_to_payload_passes_an_explicit_tool_list_straight_through(backend, context):
    sentinel = [{"name": "only_this"}]

    assert backend.to_payload(context, tools=sentinel)["tools"] == sentinel


def test_to_payload_honours_an_empty_tool_list(backend, context):
    """The §5.9 trap: [] is falsy in Python but truthy in Ruby. Branching on truthiness instead
    of `is None` would re-enable tools on exactly the call meant to disable them."""
    assert backend.to_payload(context, tools=[])["tools"] == []


# ---------- step 05: parse_response ------------------------------------------


def test_parse_response_normalizes_a_text_reply(backend):
    parsed = backend.parse_response(
        {"stop_reason": "end_turn", "content": [{"type": "text", "text": "hello"}]}
    )

    assert parsed == {"stop_reason": "end_turn", "content": [{"type": "text", "text": "hello"}]}


def test_parse_response_normalizes_a_tool_use_reply(backend):
    block = {"type": "tool_use", "id": "toolu_1", "name": "look", "input": {}}

    parsed = backend.parse_response({"stop_reason": "tool_use", "content": [block]})

    assert parsed == {"stop_reason": "tool_use", "content": [block]}


def test_parse_response_maps_any_other_stop_reason_to_end_turn(backend):
    for reason in ("max_tokens", "stop_sequence", "refusal", None):
        assert backend.parse_response({"stop_reason": reason, "content": []})["stop_reason"] == "end_turn"


def test_parse_response_defaults_missing_content_to_an_empty_list(backend):
    assert backend.parse_response({"stop_reason": "end_turn"})["content"] == []
    assert backend.parse_response({"stop_reason": "end_turn", "content": None})["content"] == []
