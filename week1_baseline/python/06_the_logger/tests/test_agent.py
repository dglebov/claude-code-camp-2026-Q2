"""Tests for `boukensha/agent.py`.

Rewritten for step 06, not extended: the agent no longer prints anything, so every step-05
assertion that read stdout is now expressed against a spy logger. See
`docs/plans/python_port/06_the_logger.md` §7.1.

`Agent` takes its collaborators by constructor injection, so nothing here needs patching.
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


def tool_use(*calls, reasoning=None):
    """calls: (id, name, input) triples."""
    content = [{"type": "text", "text": reasoning}] if reasoning else []
    content += [{"type": "tool_use", "id": i, "name": n, "input": a} for i, n, a in calls]
    return {"stop_reason": "tool_use", "content": content}


class StubClient:
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
    def __init__(self, backend=None):
        self.backend = backend

    def parse_response(self, response):
        return response


class SpyLogger:
    """Records every call as (method_name, kwargs)."""

    def __init__(self):
        self.events = []

    def __getattr__(self, name):
        def record(**kwargs):
            self.events.append((name, kwargs))

        return record

    def phases(self):
        return [name for name, _ in self.events]

    def only(self, name):
        return [kwargs for n, kwargs in self.events if n == name]


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


@pytest.fixture
def spy():
    return SpyLogger()


def build(context, registry, client, spy, **kwargs):
    return Agent(context=context, registry=registry, builder=StubBuilder(), client=client, logger=spy, **kwargs)


# ---------- terminating without tools ---------------------------------------


def test_an_end_turn_reply_returns_its_text_after_one_call(context, registry, spy):
    client = StubClient(text("All done."))

    assert build(context, registry, client, spy).run() == "All done."
    assert client.count == 1


def test_multiple_text_blocks_are_joined_with_no_separator(context, registry, spy):
    client = StubClient(
        {"stop_reason": "end_turn", "content": [{"type": "text", "text": "abc"}, {"type": "text", "text": "def"}]}
    )

    assert build(context, registry, client, spy).run() == "abcdef"


def test_non_text_blocks_are_excluded_from_the_returned_text(context, registry, spy):
    client = StubClient(
        {"stop_reason": "end_turn", "content": [{"type": "text", "text": "hi"}, {"type": "thinking", "text": "hmm"}]}
    )

    assert build(context, registry, client, spy).run() == "hi"


# ---------- the tool loop ----------------------------------------------------


def test_a_tool_use_reply_dispatches_then_loops_until_end_turn(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})), text("I looked."))

    assert build(context, registry, client, spy).run() == "I looked."
    assert client.count == 2


def test_the_tool_loop_appends_an_assistant_turn_then_a_tool_result(context, registry, spy):
    reply = tool_use(("t1", "look", {}))
    client = StubClient(reply, text("done"))

    build(context, registry, client, spy).run()

    assistant, result = context.messages[-2], context.messages[-1]
    assert assistant.role == "assistant"
    assert assistant.content == reply["content"]
    assert result.role == "tool_result"
    assert result.content == "A damp stone corridor."
    assert result.tool_use_id == "t1"


def test_every_tool_use_block_in_one_reply_is_dispatched_in_order(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {}), ("t2", "move", {"direction": "north"})), text("done"))

    build(context, registry, client, spy).run()

    assert [(k["name"], k["result"]) for k in spy.only("tool_result")] == [
        ("look", "A damp stone corridor."),
        ("move", "You move north."),
    ]


# ---------- logging replaces the stdout trace --------------------------------


def test_the_event_sequence_matches_rubys(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})), text("done"))

    build(context, registry, client, spy).run()

    assert spy.phases() == [
        "iteration",
        "prompt",
        "raw",
        "response",  # the assistant's reasoning, before the tools run
        "tool_call",
        "tool_result",
        "iteration",
        "prompt",
        "raw",
        "response",
        "turn_end",
    ]


def test_iteration_events_carry_the_counter_and_ceiling(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})), text("done"))

    build(context, registry, client, spy, max_iterations=25).run()

    assert spy.only("iteration") == [{"n": 1, "max": 25}, {"n": 2, "max": 25}]


def test_the_prompt_event_carries_the_live_message_and_tool_collections(context, registry, spy):
    client = StubClient(text("done"))

    build(context, registry, client, spy).run()

    prompt = spy.only("prompt")[0]
    assert prompt["messages"] is context.messages
    assert prompt["tools"] is context.tools


def test_tool_call_events_record_name_and_args(context, registry, spy):
    client = StubClient(tool_use(("t1", "move", {"direction": "north"})), text("done"))

    build(context, registry, client, spy).run()

    assert spy.only("tool_call") == [{"name": "move", "args": {"direction": "north"}}]


def test_assistant_reasoning_is_logged_before_the_tools_run(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {}), reasoning="Let me look."), text("done"))

    build(context, registry, client, spy).run()

    assert spy.only("response")[0]["text"] == "Let me look."


@pytest.mark.parametrize(
    "calls,expected",
    [
        ((("t1", "look", {}),), "(tool use — 1 call)"),
        ((("t1", "look", {}), ("t2", "look", {})), "(tool use — 2 calls)"),
    ],
)
def test_a_placeholder_stands_in_for_absent_reasoning(context, registry, spy, calls, expected):
    client = StubClient(tool_use(*calls), text("done"))

    build(context, registry, client, spy).run()

    assert spy.only("response")[0]["text"] == expected


# ---------- tool failures are caught -----------------------------------------


def test_a_raising_tool_is_caught_logged_and_the_loop_continues(context, registry, spy):
    reg = Registry(context)

    @reg.tool("boom", description="Always fails", parameters={})
    def boom():
        raise ValueError("kaboom")

    client = StubClient(tool_use(("t1", "boom", {})), text("recovered"))

    result = Agent(context=context, registry=reg, builder=StubBuilder(), client=client, logger=spy).run()

    assert result == "recovered"
    failure = spy.only("tool_result")[0]
    assert failure["ok"] is False
    assert failure["error"] == "kaboom"
    assert failure["result"] == "ERROR: ValueError: kaboom"
    # The error text is fed back to the model as the tool result.
    assert context.messages[-1].content == "ERROR: ValueError: kaboom"


def test_an_unknown_tool_is_caught_rather_than_propagating(context, registry, spy):
    client = StubClient(tool_use(("t1", "nope", {})), text("recovered"))

    assert build(context, registry, client, spy).run() == "recovered"
    assert spy.only("tool_result")[0]["ok"] is False


# ---------- the iteration ceiling and wind-down ------------------------------


def test_reaching_max_iterations_makes_exactly_one_wind_down_call(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})), tool_use(("t2", "look", {})), text("Out of actions."))

    result = build(context, registry, client, spy, max_iterations=2).run()

    assert client.count == 3
    assert client.calls[-1] == {"tools": [], "max_output_tokens": 400}
    assert result == "Out of actions."


def test_limit_reached_fires_once_immediately_before_the_wind_down(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})))

    build(context, registry, client, spy, max_iterations=1).run()

    assert spy.only("limit_reached") == [{"kind": "max_iterations", "n": 1, "max": 1}]
    assert spy.phases().index("limit_reached") < spy.phases().index("turn_end")


def test_the_wind_down_call_disables_tools_with_an_empty_list_not_none(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})))

    build(context, registry, client, spy, max_iterations=1).run()

    assert client.calls[-1]["tools"] == []


def test_the_wind_down_appends_the_directive_as_a_user_turn(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})))

    build(context, registry, client, spy, max_iterations=1).run()

    directives = [m for m in context.messages if m.role == "user" and "action limit" in str(m.content)]
    assert len(directives) == 1
    assert directives[0].content == Agent.WRAP_UP_DIRECTIVE


def test_the_wind_down_does_not_count_as_an_iteration(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})))

    agent = build(context, registry, client, spy, max_iterations=2)
    agent.run()

    assert spy.only("iteration") == [{"n": 1, "max": 2}, {"n": 2, "max": 2}]
    assert agent._iteration == 2


@pytest.mark.parametrize(
    "third",
    [text("wrapped"), ApiError("503")],
    ids=["wind_down_succeeds", "wind_down_raises"],
)
def test_turn_end_fires_exactly_once_on_every_exit_path(context, registry, spy, third):
    client = StubClient(tool_use(("t1", "look", {})), third)

    build(context, registry, client, spy, max_iterations=1).run()

    assert spy.only("turn_end") == [{"reason": "max_iterations", "iterations": 1}]


def test_turn_end_reports_completed_when_the_model_stops_on_its_own(context, registry, spy):
    client = StubClient(text("done"))

    build(context, registry, client, spy).run()

    assert spy.only("turn_end") == [{"reason": "completed", "iterations": 1}]


def test_an_api_error_during_wind_down_returns_the_fallback(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})), tool_use(("t2", "look", {})), ApiError("503"))

    result = build(context, registry, client, spy, max_iterations=2).run()

    assert result == (
        "I reached my 2-action limit for this turn before finishing "
        "(max_iterations). Ask me to continue and I'll pick up from here."
    )


@pytest.mark.parametrize("body", ["", "   ", "\n\t "])
def test_an_empty_wind_down_reply_returns_the_fallback(context, registry, spy, body):
    client = StubClient(tool_use(("t1", "look", {})), text(body))

    assert "1-action limit" in build(context, registry, client, spy, max_iterations=1).run()


def test_max_iterations_of_zero_disables_the_ceiling(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})), text("done"))

    assert build(context, registry, client, spy, max_iterations=0).run() == "done"
    assert client.count == 2


# ---------- usage normalization ----------------------------------------------


@pytest.mark.parametrize(
    "response_extra,expected",
    [
        ({"usage": {"input_tokens": 1}}, {"input_tokens": 1}),
        ({"usageMetadata": {"promptTokenCount": 2}}, {"promptTokenCount": 2}),
        ({"prompt_eval_count": 3, "eval_count": 4}, {"prompt_eval_count": 3, "eval_count": 4}),
        ({}, None),
    ],
)
def test_usage_is_normalized_across_provider_shapes(context, registry, spy, response_extra, expected):
    reply = {"stop_reason": "end_turn", "content": [{"type": "text", "text": "x"}], **response_extra}
    client = StubClient(reply)

    build(context, registry, client, spy).run()

    assert spy.only("response")[0]["usage"] == expected


def test_the_response_event_carries_the_task_and_backend(context, registry, spy):
    backend = object()
    client = StubClient(text("done"))

    Agent(context=context, registry=registry, builder=StubBuilder(backend), client=client, logger=spy).run()

    event = spy.only("response")[0]
    assert event["task"] is Player
    assert event["backend"] is backend
    assert event["stop_reason"] == "end_turn"


# ---------- resolving the bounds ---------------------------------------------


def test_an_explicit_argument_wins_over_task_settings(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})), text("done"))

    build(context, registry, client, spy, task_settings={"max_iterations": 9}, max_iterations=3).run()

    assert spy.only("iteration")[0]["max"] == 3


def test_task_settings_win_over_the_class_default(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})), text("done"))

    build(context, registry, client, spy, task_settings={"max_iterations": 9}).run()

    assert spy.only("iteration")[0]["max"] == 9


def test_the_class_default_applies_with_no_settings_and_no_argument(context, registry, spy):
    client = StubClient(text("done"))

    build(context, registry, client, spy).run()

    assert spy.only("iteration")[0]["max"] == Agent.MAX_ITERATIONS


def test_max_output_tokens_from_settings_is_sent_on_every_counted_call(context, registry, spy):
    client = StubClient(tool_use(("t1", "look", {})), text("done"))

    build(context, registry, client, spy, task_settings={"max_output_tokens": 256}).run()

    assert client.calls[0] == {"max_output_tokens": 256}
    assert client.calls[1] == {"max_output_tokens": 256}


def test_no_max_output_tokens_means_the_call_carries_no_override(context, registry, spy):
    client = StubClient(text("done"))

    build(context, registry, client, spy).run()

    assert client.calls[0] == {}


def test_a_task_without_the_settings_readers_falls_back_to_the_constant(context, registry, spy):
    class LegacyTask:
        @classmethod
        def task_name(cls):
            return "legacy"

    context.task = LegacyTask
    client = StubClient(text("done"))

    build(context, registry, client, spy, task_settings={"max_iterations": 9}).run()

    assert spy.only("iteration")[0]["max"] == Agent.MAX_ITERATIONS


# ---------- the default logger -----------------------------------------------


def test_each_agent_gets_its_own_logger_when_none_is_passed(context, registry, tmp_path, monkeypatch):
    """A Python default of `logger=Logger()` would build ONE at import time, shared by every
    Agent, and would open a log file as a side effect of importing the module (plan §5.10)."""
    import boukensha

    monkeypatch.setattr(boukensha, "_config", None)
    monkeypatch.setenv("BOUKENSHA_DIR", str(tmp_path))

    client = StubClient(text("done"))
    a = Agent(context=context, registry=registry, builder=StubBuilder(), client=client)
    b = Agent(context=context, registry=registry, builder=StubBuilder(), client=client)

    assert a._logger is not b._logger
    assert a._logger.path != b._logger.path
