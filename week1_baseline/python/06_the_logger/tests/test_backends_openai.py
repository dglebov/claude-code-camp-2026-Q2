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


def _reply(message):
    return {"choices": [{"message": message}]}


def test_parse_response_normalizes_a_text_reply(backend):
    parsed = backend.parse_response(_reply({"content": "hello"}))

    assert parsed == {"stop_reason": "end_turn", "content": [{"type": "text", "text": "hello"}]}


def test_parse_response_normalizes_tool_calls_and_json_decodes_arguments(backend):
    parsed = backend.parse_response(
        _reply(
            {
                "content": None,
                "tool_calls": [
                    {"id": "call_1", "function": {"name": "move", "arguments": '{"direction":"north"}'}}
                ],
            }
        )
    )

    assert parsed == {
        "stop_reason": "tool_use",
        "content": [{"type": "tool_use", "id": "call_1", "name": "move", "input": {"direction": "north"}}],
    }


def test_parse_response_defaults_absent_arguments_to_an_empty_dict(backend):
    parsed = backend.parse_response(
        _reply({"content": None, "tool_calls": [{"id": "c", "function": {"name": "look"}}]})
    )

    assert parsed["content"][0]["input"] == {}


def test_parse_response_keeps_text_alongside_tool_calls(backend):
    parsed = backend.parse_response(
        _reply(
            {
                "content": "let me look",
                "tool_calls": [{"id": "c", "function": {"name": "look", "arguments": "{}"}}],
            }
        )
    )

    assert [b["type"] for b in parsed["content"]] == ["text", "tool_use"]
    assert parsed["stop_reason"] == "tool_use"


def test_parse_response_emits_a_text_block_for_an_empty_string(backend):
    """Ruby guards with a bare `if message["content"]`, and "" is TRUTHY in Ruby — so an empty
    string still produces a block. Mirrored with `is not None`; a plain `if` would drop it, and
    would silently disagree with Ollama's version, which guards differently on purpose."""
    parsed = backend.parse_response(_reply({"content": ""}))

    assert parsed["content"] == [{"type": "text", "text": ""}]


def test_parse_response_tolerates_a_missing_choices_array(backend):
    assert backend.parse_response({}) == {"stop_reason": "end_turn", "content": []}
