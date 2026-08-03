"""Tests for `boukensha/agent.py`.

Ruby step 05 ships no specs, so these have no counterpart to mirror — see
`docs/plans/python_port/05_agent_loop.md` §7.1.

`Agent` takes its collaborators by constructor injection, so unlike `Client` it needs no
patching: a stub client replaying scripted replies drives every path. The scripted replies are
already in the normalized shape, so the stub builder's `parse_response` is a pass-through.
"""

import pytest
from boukensha.agent import Agent
from boukensha.context import Context
from boukensha.errors import ApiError
from boukensha.registry import Registry
from boukensha.tasks import Player

SYSTEM = "You are a MUD player assistant."


def text(body):
    return {"stop_reason": "end_turn", "content": [{"type": "text", "text": body}]}


def tool_use(*calls):
    """calls: (id, name, input) triples."""
    return {
        "stop_reason": "tool_use",
        "content": [{"type": "tool_use", "id": i, "name": n, "input": a} for i, n, a in calls],
    }


class StubClient:
    """Replays a script. Records the kwargs of every call so the wind-down call can be asserted."""

    def __init__(self, *script):
        self.script = list(script)
        self.calls = []

    def call(self, **kwargs):
        self.calls.append(kwargs)
        entry = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(entry, Exception):
            raise entry
        return entry

    @property
    def count(self):
        return len(self.calls)


class StubBuilder:
    def parse_response(self, response):
        return response


@pytest.fixture
def context():
    return Context(task=Player, system=SYSTEM)


@pytest.fixture
def registry(context):
    reg = Registry(context)

    @reg.tool("look", description="Look around", parameters={})
    def look():
        return "A damp stone corridor."

    @reg.tool(
        "move",
        description="Move the player",
        parameters={"direction": {"type": "string", "description": "Direction"}},
    )
    def move(*, direction):
        return f"You move {direction}."

    return reg


def build(context, registry, client, **kwargs):
    return Agent(context=context, registry=registry, builder=StubBuilder(), client=client, **kwargs)


# ---------- terminating without tools ---------------------------------------


def test_an_end_turn_reply_returns_its_text_after_one_call(context, registry):
    client = StubClient(text("All done."))

    assert build(context, registry, client).run() == "All done."
    assert client.count == 1


def test_multiple_text_blocks_are_joined_with_no_separator(context, registry):
    """Ruby's bare `.join` uses "", not ", " (plan §5.7)."""
    client = StubClient(
        {"stop_reason": "end_turn", "content": [{"type": "text", "text": "abc"}, {"type": "text", "text": "def"}]}
    )

    assert build(context, registry, client).run() == "abcdef"


def test_non_text_blocks_are_excluded_from_the_returned_text(context, registry):
    client = StubClient(
        {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "hi"}, {"type": "thinking", "text": "hmm"}],
        }
    )

    assert build(context, registry, client).run() == "hi"


# ---------- the tool loop ----------------------------------------------------


def test_a_tool_use_reply_dispatches_then_loops_until_end_turn(context, registry):
    client = StubClient(tool_use(("t1", "look", {})), text("I looked."))

    assert build(context, registry, client).run() == "I looked."
    assert client.count == 2


def test_the_tool_loop_appends_an_assistant_turn_then_a_tool_result(context, registry):
    reply = tool_use(("t1", "look", {}))
    client = StubClient(reply, text("done"))

    build(context, registry, client).run()

    assistant, result = context.messages[-2], context.messages[-1]
    assert assistant.role == "assistant"
    # The whole normalized content list is stored, not just its text — Anthropic requires the
    # tool_use block to precede its result.
    assert assistant.content == reply["content"]
    assert result.role == "tool_result"
    assert result.content == "A damp stone corridor."
    assert result.tool_use_id == "t1"


def test_every_tool_use_block_in_one_reply_is_dispatched_in_order(context, registry):
    client = StubClient(
        tool_use(("t1", "look", {}), ("t2", "move", {"direction": "north"})),
        text("done"),
    )

    build(context, registry, client).run()

    results = [m for m in context.messages if m.role == "tool_result"]
    assert [(m.tool_use_id, m.content) for m in results] == [
        ("t1", "A damp stone corridor."),
        ("t2", "You move north."),
    ]


def test_the_trace_matches_rubys_format(context, registry, capsys):
    client = StubClient(tool_use(("t1", "move", {"direction": "north"})), text("done"))

    build(context, registry, client, max_iterations=25).run()

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "[iteration 1/25]"
    assert lines[1] == "  tool call → move({'direction': 'north'})"
    assert lines[2] == "  tool result → You move north."
    assert lines[3] == "[iteration 2/25]"


def test_the_tool_result_trace_truncates_at_61_characters(context, registry, capsys):
    """Ruby's `[0..60]` is inclusive — 61 characters, not 60 (plan §5.6)."""
    reg = Registry(context)

    @reg.tool("long", description="Returns a long string", parameters={})
    def long_tool():
        return "x" * 200

    client = StubClient(tool_use(("t1", "long", {})), text("done"))
    build(context, reg, client).run()

    trace = next(ln for ln in capsys.readouterr().out.splitlines() if "tool result" in ln)
    assert trace == "  tool result → " + "x" * 61


# ---------- the iteration ceiling and wind-down ------------------------------


def test_reaching_max_iterations_makes_exactly_one_wind_down_call(context, registry):
    # Two tool-use replies exhaust the ceiling; the third entry is what the wind-down call gets.
    client = StubClient(
        tool_use(("t1", "look", {})),
        tool_use(("t2", "look", {})),
        text("I looked around twice and ran out of actions."),
    )

    result = build(context, registry, client, max_iterations=2).run()

    # 2 counted iterations + 1 wind-down
    assert client.count == 3
    assert client.calls[-1] == {"tools": [], "max_output_tokens": 400}
    assert result == "I looked around twice and ran out of actions."


def test_the_wind_down_call_disables_tools_with_an_empty_list_not_none(context, registry):
    """The §5.9 trap: `tools=[]` must survive as [], never be coerced to None."""
    client = StubClient(tool_use(("t1", "look", {})))

    build(context, registry, client, max_iterations=1).run()

    assert client.calls[-1]["tools"] == []
    assert client.calls[-1]["tools"] is not None


def test_the_wind_down_appends_the_directive_as_a_user_turn(context, registry):
    client = StubClient(tool_use(("t1", "look", {})))

    build(context, registry, client, max_iterations=1).run()

    directives = [m for m in context.messages if m.role == "user" and "action limit" in str(m.content)]
    assert len(directives) == 1
    assert directives[0].content == Agent.WRAP_UP_DIRECTIVE


def test_the_wind_down_does_not_count_as_an_iteration(context, registry, capsys):
    client = StubClient(tool_use(("t1", "look", {})))

    agent = build(context, registry, client, max_iterations=2)
    agent.run()

    iterations = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("[iteration")]
    assert iterations == ["[iteration 1/2]", "[iteration 2/2]"]
    # Assert the counter itself, not just the trace: the wind-down prints nothing, so an
    # increment inside it is invisible to the lines above.
    assert agent._iteration == 2


def test_an_api_error_during_wind_down_returns_the_fallback(context, registry):
    client = StubClient(tool_use(("t1", "look", {})), tool_use(("t2", "look", {})), ApiError("503"))

    result = build(context, registry, client, max_iterations=2).run()

    assert result == (
        "I reached my 2-action limit for this turn before finishing "
        "(max_iterations). Ask me to continue and I'll pick up from here."
    )


@pytest.mark.parametrize("body", ["", "   ", "\n\t "])
def test_an_empty_wind_down_reply_returns_the_fallback(context, registry, body):
    client = StubClient(tool_use(("t1", "look", {})), text(body))

    result = build(context, registry, client, max_iterations=1).run()

    assert "1-action limit" in result


def test_max_iterations_of_zero_disables_the_ceiling(context, registry):
    """0 means "no ceiling", not "no iterations" (plan §5.5)."""
    client = StubClient(tool_use(("t1", "look", {})), text("done"))

    assert build(context, registry, client, max_iterations=0).run() == "done"
    assert client.count == 2


# ---------- resolving the bounds ---------------------------------------------


def test_an_explicit_argument_wins_over_task_settings(context, registry, capsys):
    client = StubClient(tool_use(("t1", "look", {})), text("done"))

    build(context, registry, client, task_settings={"max_iterations": 9}, max_iterations=3).run()

    assert capsys.readouterr().out.splitlines()[0] == "[iteration 1/3]"


def test_task_settings_win_over_the_class_default(context, registry, capsys):
    client = StubClient(tool_use(("t1", "look", {})), text("done"))

    build(context, registry, client, task_settings={"max_iterations": 9}).run()

    assert capsys.readouterr().out.splitlines()[0] == "[iteration 1/9]"


def test_the_class_default_applies_with_no_settings_and_no_argument(context, registry, capsys):
    client = StubClient(text("done"))

    build(context, registry, client).run()

    assert capsys.readouterr().out.splitlines()[0] == f"[iteration 1/{Agent.MAX_ITERATIONS}]"


def test_max_output_tokens_from_settings_is_sent_on_every_counted_call(context, registry):
    client = StubClient(tool_use(("t1", "look", {})), text("done"))

    build(context, registry, client, task_settings={"max_output_tokens": 256}).run()

    assert client.calls[0] == {"max_output_tokens": 256}
    assert client.calls[1] == {"max_output_tokens": 256}


def test_no_max_output_tokens_means_the_call_carries_no_override(context, registry):
    """Ruby's resolve_max_output_tokens falls back to nil, not to a constant (plan §8)."""
    client = StubClient(text("done"))

    build(context, registry, client).run()

    assert client.calls[0] == {}


def test_a_task_without_the_settings_readers_falls_back_to_the_constant(context, registry, capsys):
    class LegacyTask:
        @classmethod
        def task_name(cls):
            return "legacy"

    context.task = LegacyTask
    client = StubClient(text("done"))

    build(context, registry, client, task_settings={"max_iterations": 9}).run()

    assert capsys.readouterr().out.splitlines()[0] == f"[iteration 1/{Agent.MAX_ITERATIONS}]"
