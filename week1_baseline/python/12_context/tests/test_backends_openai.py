"""Tests for `boukensha/backends/openai.py`.

**Rewritten for step 12.** The backend moved from `/v1/chat/completions` to the **Responses API**
(`/v1/responses`), because gpt-5.x rejects `reasoning_effort` together with tools on chat
completions. Every shape in this file changed with it:

  * the system prompt is a top-level `instructions` string, not a first message
  * messages become `input` items
  * tool definitions are flat — no `function:` envelope
  * tool results are `function_call_output` items matched by `call_id`
  * responses are an `output[]` array of typed items, not `choices[0].message`
"""

import json

import pytest
from boukensha.backends import OpenAI
from boukensha.errors import UnsupportedModelError

# Mirrors the values conftest.py builds the shared `context` fixture from. Kept literal here so
# a drift in either place fails loudly rather than silently agreeing with itself.
SYSTEM = "You are a MUD player assistant."
LOOK_RESULT = "A damp stone corridor stretches north."

MODEL = "gpt-5.4-mini"


@pytest.fixture
def backend():
    return OpenAI(api_key="sk-test", model=MODEL)


# ---------- model table ------------------------------------------------------


def test_rejects_an_unknown_model():
    with pytest.raises(UnsupportedModelError):
        OpenAI(api_key="sk-test", model="gpt-4")


def test_model_metadata(backend):
    assert backend.context_window == 400_000
    assert backend.usage_unit == "tokens"
    # 0.75 in + 4.5 out, per million.
    assert backend.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000) == 5.25


def test_the_nano_model_is_available():
    """Step 12 swapped gpt-5.4 out of the table for gpt-5.4-nano."""
    nano = OpenAI(api_key="sk-test", model="gpt-5.4-nano")
    assert nano.context_window == 400_000


# ---------- request shaping --------------------------------------------------


def test_to_tools_is_flat_with_no_function_envelope(backend, context):
    tools = backend.to_tools(context.tools)

    assert [t["type"] for t in tools] == ["function", "function"]
    assert [t["name"] for t in tools] == ["look", "move"]
    # The Responses API puts name/description/parameters at the top level of the tool object;
    # chat completions nested them under "function".
    assert "function" not in tools[0]
    assert tools[1]["parameters"]["required"] == ["direction"]


def test_to_input_omits_the_system_prompt(backend, context):
    """`instructions` carries it instead — a system message in `input` would duplicate it."""
    items = backend.to_input(context.messages)

    assert all(item.get("role") != "system" for item in items)


def test_to_input_turns_a_tool_result_into_a_function_call_output(backend, context):
    items = backend.to_input(context.messages)

    result = [i for i in items if i.get("type") == "function_call_output"]
    assert result == [{"type": "function_call_output", "call_id": "toolu_01X", "output": LOOK_RESULT}]


def test_to_payload(backend, context):
    payload = backend.to_payload(context)

    assert payload["model"] == MODEL
    assert payload["instructions"] == SYSTEM
    assert payload["max_output_tokens"] == 1024
    assert payload["reasoning"] == {"effort": "none"}
    assert isinstance(payload["input"], list)


def test_to_payload_honours_max_output_tokens(backend, context):
    assert backend.to_payload(context, max_output_tokens=32)["max_output_tokens"] == 32


def test_to_payload_serializes_the_contexts_tools_by_default(backend, context):
    assert backend.to_payload(context)["tools"] == backend.to_tools(context.tools)


def test_to_payload_passes_an_explicit_tool_list_straight_through(backend, context):
    assert backend.to_payload(context, tools=[{"type": "function", "name": "x"}])["tools"] == [
        {"type": "function", "name": "x"}
    ]


def test_to_payload_honours_an_empty_tool_list(backend, context):
    """[] must disable tools, not fall back to the context's — the wind-down call depends on it."""
    assert backend.to_payload(context, tools=[])["tools"] == []


def test_headers_and_url(backend):
    assert backend.url() == "https://api.openai.com/v1/responses"
    assert backend.headers()["Authorization"] == "Bearer sk-test"


# ---------- assistant round-trip ---------------------------------------------


def test_an_assistant_tool_use_round_trips_as_a_function_call(backend, empty_context):
    empty_context.add_message(
        "assistant",
        [
            {"type": "text", "text": "Looking now."},
            {"type": "tool_use", "id": "call_1", "name": "look", "input": {"target": "altar"}},
        ],
    )

    items = backend.to_input(empty_context.messages)

    assert items[0] == {"role": "assistant", "content": "Looking now."}
    assert items[1]["type"] == "function_call"
    assert items[1]["call_id"] == "call_1"
    assert json.loads(items[1]["arguments"]) == {"target": "altar"}


def test_reasoning_is_not_echoed_back(backend, empty_context):
    """gpt-5.x does not want reasoning replayed while effort is "none" — the opposite of
    Anthropic, which rejects a thinking block whose signature was dropped."""
    empty_context.add_message(
        "assistant",
        [{"type": "reasoning", "text": "thinking..."}, {"type": "text", "text": "done"}],
    )

    items = backend.to_input(empty_context.messages)

    assert items == [{"role": "assistant", "content": "done"}]


# ---------- response parsing -------------------------------------------------


def test_parse_response_normalizes_a_text_reply(backend):
    parsed = backend.parse_response(
        {"output": [{"type": "message", "content": [{"type": "output_text", "text": "a room"}]}]}
    )

    assert parsed == {"stop_reason": "end_turn", "content": [{"type": "text", "text": "a room"}]}


def test_parse_response_normalizes_reasoning_from_summary_fragments(backend):
    parsed = backend.parse_response(
        {"output": [{"type": "reasoning", "summary": [{"text": "first "}, {"text": "second"}]}]}
    )

    assert parsed["content"] == [{"type": "reasoning", "text": "first second"}]


def test_parse_response_normalizes_tool_calls_and_json_decodes_arguments(backend):
    parsed = backend.parse_response(
        {
            "output": [
                {
                    "type": "function_call",
                    "call_id": "call_9",
                    "name": "move",
                    "arguments": '{"direction": "north"}',
                }
            ]
        }
    )

    assert parsed["stop_reason"] == "tool_use"
    assert parsed["content"] == [
        {"type": "tool_use", "id": "call_9", "name": "move", "input": {"direction": "north"}}
    ]


def test_parse_response_defaults_absent_arguments_to_an_empty_dict(backend):
    parsed = backend.parse_response(
        {"output": [{"type": "function_call", "call_id": "c", "name": "look"}]}
    )

    assert parsed["content"][0]["input"] == {}


def test_parse_response_puts_tool_calls_after_text(backend):
    """Ruby collects function_calls during the pass and appends them afterwards, so ordering is
    text/reasoning first regardless of what the provider sent."""
    parsed = backend.parse_response(
        {
            "output": [
                {"type": "function_call", "call_id": "c", "name": "look", "arguments": "{}"},
                {"type": "message", "content": [{"type": "output_text", "text": "before"}]},
            ]
        }
    )

    assert [b["type"] for b in parsed["content"]] == ["text", "tool_use"]


def test_parse_response_drops_an_empty_message(backend):
    """Ruby's `unless text.empty?` inside filter_map removes the block entirely."""
    parsed = backend.parse_response(
        {"output": [{"type": "message", "content": [{"type": "output_text", "text": ""}]}]}
    )

    assert parsed["content"] == []


def test_parse_response_tolerates_a_missing_output_array(backend):
    assert backend.parse_response({}) == {"stop_reason": "end_turn", "content": []}
