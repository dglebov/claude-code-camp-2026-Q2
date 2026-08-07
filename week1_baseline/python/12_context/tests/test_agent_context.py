"""Tests for step 12's agent behaviour: the token ceiling, compaction, and reasoning logging.

Ruby step 12 ships no specs — see `docs/plans/python_port/12_context.md` §7.

Kept separate from `test_agent.py` so that file stays diffable against step 11's copy. Nothing
here touches the network: a stub client returns canned responses.
"""

import pytest
from boukensha.agent import Agent
from boukensha.context import Context
from boukensha.registry import Registry


class SpyLogger:
    def __init__(self):
        self.events = []

    def __getattr__(self, name):
        def record(**kwargs):
            self.events.append({"phase": name, **kwargs})

        return record

    def only(self, phase):
        return [e for e in self.events if e["phase"] == phase]


class StubBuilder:
    backend = None

    @staticmethod
    def parse_response(response):
        return {"stop_reason": response["stop_reason"], "content": response["content"]}


class StubClient:
    """Replays canned responses; repeats the last one forever so a loop cannot run off the end."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.calls = []

    def call(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses[min(len(self.calls) - 1, len(self._responses) - 1)]


def text(body, *, input_tokens=0, output_tokens=0):
    return {
        "stop_reason": "end_turn",
        "content": [{"type": "text", "text": body}],
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }


def tool_use(*, input_tokens=0, output_tokens=0):
    return {
        "stop_reason": "tool_use",
        "content": [{"type": "tool_use", "id": "t1", "name": "noop", "input": {}}],
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }


@pytest.fixture
def spy():
    return SpyLogger()


def build(context, client, spy, **kwargs):
    registry = Registry(context)
    registry.tool("noop", description="does nothing", parameters={})(lambda: "done")
    return Agent(
        context=context,
        registry=registry,
        builder=StubBuilder(),
        client=client,
        logger=spy,
        **kwargs,
    )


# ---------- the token ceiling ------------------------------------------------


def test_the_turn_token_ceiling_trips_and_winds_down(spy):
    ctx = Context(system="t")
    client = StubClient(tool_use(input_tokens=4_000, output_tokens=500))

    build(ctx, client, spy, max_turn_tokens=9_000).run()

    limit = spy.only("limit_reached")
    assert limit[0]["kind"] == "max_tokens"
    assert limit[0]["max"] == 9_000
    assert limit[0]["n"] >= 9_000


def test_the_reported_total_includes_the_wind_down_call(spy):
    """The trigger is evaluated on pre-wind-down spend; the wind-down call is still billed, so a
    finished turn can report more than max_turn_tokens. Ruby documents this explicitly."""
    ctx = Context(system="t")
    client = StubClient(tool_use(input_tokens=4_000, output_tokens=500))

    build(ctx, client, spy, max_turn_tokens=9_000).run()

    assert ctx.turn_tokens > 9_000


def test_zero_disables_the_token_ceiling(spy):
    ctx = Context(system="t")
    client = StubClient(text("done", input_tokens=100_000, output_tokens=100_000))

    build(ctx, client, spy, max_turn_tokens=0).run()

    assert spy.only("limit_reached") == []


def test_no_ceiling_by_default(spy):
    """Ruby's `max_turn_tokens.to_i` turns nil into 0, i.e. disabled."""
    ctx = Context(system="t")
    client = StubClient(text("done", input_tokens=99_999, output_tokens=99_999))

    build(ctx, client, spy).run()

    assert spy.only("limit_reached") == []


def test_turn_tokens_are_reset_at_the_start_of_each_turn(spy):
    ctx = Context(system="t")
    ctx.add_turn_tokens(50_000, 0)  # left over from a previous turn
    client = StubClient(text("done", input_tokens=10, output_tokens=1))

    build(ctx, client, spy).run()

    assert ctx.turn_tokens == 11


# ---------- compaction -------------------------------------------------------


def test_compaction_fires_before_the_first_call_when_the_window_is_full(spy):
    ctx = Context(system="t", context_window=10_000, compaction_threshold=0.5)
    for i in range(10):
        ctx.add_message("user", f"m{i}")
    ctx.update_tokens(9_000)
    client = StubClient(text("done"))

    build(ctx, client, spy).run()

    event = spy.only("compaction")
    assert len(event) == 1
    assert event[0]["before"] == 9_000
    assert event[0]["dropped"] == 4
    assert event[0]["context_window"] == 10_000


def test_no_compaction_when_the_window_is_comfortable(spy):
    ctx = Context(system="t", context_window=10_000, compaction_threshold=0.85)
    for i in range(10):
        ctx.add_message("user", f"m{i}")
    ctx.update_tokens(1_000)
    client = StubClient(text("done"))

    build(ctx, client, spy).run()

    assert spy.only("compaction") == []


def test_usage_is_refreshed_from_the_response(spy):
    ctx = Context(system="t", context_window=10_000)
    client = StubClient(text("done", input_tokens=2_500, output_tokens=10))

    build(ctx, client, spy).run()

    assert ctx.current_tokens == 2_500
    assert ctx.usage_pct() == 25


# ---------- reasoning --------------------------------------------------------


def reasoning_response(*blocks):
    return {"stop_reason": "end_turn", "content": [*blocks, {"type": "text", "text": "done"}],
            "usage": {"input_tokens": 1, "output_tokens": 1}}


def test_a_reasoning_block_is_logged(spy):
    ctx = Context(system="t")
    client = StubClient(reasoning_response({"type": "reasoning", "text": "thinking hard"}))

    build(ctx, client, spy).run()

    assert spy.only("reasoning") == [
        {"phase": "reasoning", "text": "thinking hard", "redacted": False}
    ]


def test_an_empty_reasoning_block_is_skipped(spy):
    ctx = Context(system="t")
    client = StubClient(reasoning_response({"type": "reasoning", "text": "   "}))

    build(ctx, client, spy).run()

    assert spy.only("reasoning") == []


def test_a_redacted_block_is_logged_even_with_no_text(spy):
    """It carries no words, but it tells the reader the model thought here. That asymmetry with
    the empty case is the whole point of logging redacted blocks at all."""
    ctx = Context(system="t")
    client = StubClient(reasoning_response({"type": "reasoning", "text": "", "redacted": True}))

    build(ctx, client, spy).run()

    assert spy.only("reasoning") == [{"phase": "reasoning", "text": "", "redacted": True}]


def test_non_reasoning_blocks_are_ignored(spy):
    ctx = Context(system="t")
    client = StubClient(text("done"))

    build(ctx, client, spy).run()

    assert spy.only("reasoning") == []


# ---------- the prompt event -------------------------------------------------


def test_the_prompt_event_carries_the_context_window(spy):
    ctx = Context(system="t", context_window=123_456)
    client = StubClient(text("done"))

    build(ctx, client, spy).run()

    assert spy.only("prompt")[0]["context_window"] == 123_456
