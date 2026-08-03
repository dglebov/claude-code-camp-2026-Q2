import pytest
from boukensha.backends import OllamaCloud
from boukensha.errors import UnsupportedModelError

# Mirrors the values conftest.py builds the shared `context` fixture from. Kept literal here so
# a drift in either place fails loudly rather than silently agreeing with itself.
SYSTEM = "You are a MUD player assistant."
LOOK_RESULT = "A damp stone corridor stretches north."

MODEL = "kimi-k2.5:cloud"


@pytest.fixture
def backend():
    return OllamaCloud(api_key="sk-test", model=MODEL)


def test_rejects_an_unknown_model():
    with pytest.raises(UnsupportedModelError):
        OllamaCloud(api_key="sk-test", model="kimi-k2")


def test_model_metadata(backend):
    assert backend.context_window == 256_000
    assert backend.usage_unit == "ollama_cloud_usage"
    assert backend.usage_level == "high"


def test_cost_is_unknown_not_zero(backend):
    """Cloud pricing is plan-based rather than per token, so both sides are genuinely None."""
    assert backend.input_token_cost_per_million is None
    assert backend.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000) is None


def test_advertised_context_window_is_recorded_where_it_differs():
    backend = OllamaCloud(api_key="sk-test", model="minimax-m3:cloud")

    assert backend.context_window == 512_000
    assert backend.model_info["advertised_context_window"] == 1_000_000


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


def test_to_messages_matches_local_ollama(backend, context):
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


def test_headers_and_url(backend):
    assert backend.headers() == {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-test",
    }
    assert backend.url() == "https://ollama.com/api/chat"


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
    parsed = backend.parse_response({"message": {"content": "hello"}})

    assert parsed == {"stop_reason": "end_turn", "content": [{"type": "text", "text": "hello"}]}


def test_parse_response_reuses_the_function_name_as_the_call_id(backend):
    parsed = backend.parse_response(
        {"message": {"content": "", "tool_calls": [{"function": {"name": "move", "arguments": {"direction": "north"}}}]}}
    )

    assert parsed == {
        "stop_reason": "tool_use",
        "content": [{"type": "tool_use", "id": "move", "name": "move", "input": {"direction": "north"}}],
    }


def test_parse_response_skips_an_empty_text_block(backend):
    """Ruby guards with `content && !content.empty?` here — unlike OpenAI's bare truthiness
    check, which keeps the empty string. The two backends genuinely differ."""
    assert backend.parse_response({"message": {"content": ""}})["content"] == []


def test_parse_response_defaults_absent_arguments_to_an_empty_dict(backend):
    parsed = backend.parse_response({"message": {"tool_calls": [{"function": {"name": "look"}}]}})

    assert parsed["content"][0]["input"] == {}


def test_parse_response_tolerates_a_missing_message(backend):
    assert backend.parse_response({}) == {"stop_reason": "end_turn", "content": []}
