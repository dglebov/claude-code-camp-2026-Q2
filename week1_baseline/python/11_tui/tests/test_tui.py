"""Tests for `boukensha/tui.py` and the step-11 seams on `Repl`.

Ruby step 11 ships no specs — see `docs/plans/python_port/11_tui.md` §7.

Nothing here launches a full-screen app. A `Tui` is constructible without being run, so the state
machine (`_handle_event`) and the renderers are exercised directly with `_write` stubbed out;
that is where all the logic worth testing lives. Driving the actual widgets would need Textual's
async pilot and a pytest-asyncio dependency, and would test Textual rather than this port.
"""

import importlib
import io
import threading

import boukensha
import pytest
from boukensha.context import Context
from boukensha.errors import Interrupted
from boukensha.registry import Registry
from boukensha.repl import Repl
from boukensha.tasks import Player
from boukensha.tui import SPINNER_FRAMES, Tui, fmt_tokens

REPL_MODULE = importlib.import_module("boukensha.repl")


# ---------- doubles ----------------------------------------------------------


class FakeLogger:
    def __init__(self):
        self.turns = []
        self.subscribers = []
        self.turn_ends = []

    def turn(self, *, n):
        self.turns.append(n)

    def subscribe(self, callback):
        self.subscribers.append(callback)

    def turn_end(self, **kwargs):
        self.turn_ends.append(kwargs)

    def close(self):
        pass


class FakeAgent:
    reply = "a fake reply"

    def __init__(self, *, context, **_kwargs):
        self._context = context

    def run(self):
        self._context.add_message("assistant", self.reply)
        return self.reply


@pytest.fixture
def ctx():
    return Context(task=Player, system="t")


@pytest.fixture
def logger():
    return FakeLogger()


@pytest.fixture
def repl(ctx, logger):
    return Repl(
        context=ctx,
        registry=Registry(ctx),
        builder=None,
        client=None,
        logger=logger,
        provider="anthropic",
        model="claude-haiku-4-5",
        version="0.11.0",
        api_key="sk-test",
    )


@pytest.fixture
def tui(repl):
    """A Tui wired to a real Repl, with widget writes captured instead of rendered."""
    app = Tui(repl)
    app.written = []
    app._write = app.written.append
    return app


# ---------- Repl: the output seam --------------------------------------------


def test_on_output_captures_everything_and_stdout_stays_empty(repl, capsys, monkeypatch):
    captured = []
    repl.on_output(captured.append)
    monkeypatch.setattr("sys.stdin", io.StringIO("/help\n/exit\n"))

    repl.start()

    assert any("BOUKENSHA MUD Assistant" in line for line in captured)
    assert any("/quiet   suppress logging output" in line for line in captured)
    assert "Goodbye." in captured
    assert capsys.readouterr().out == ""


def test_without_a_callback_output_still_reaches_stdout(repl, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("/exit\n"))

    repl.start()

    assert "Goodbye." in capsys.readouterr().out


def test_the_prompt_is_suppressed_when_a_callback_is_registered(repl, capsys, monkeypatch):
    repl.on_output(lambda _text: None)
    monkeypatch.setattr("sys.stdin", io.StringIO("/exit\n"))

    repl.start()

    assert Repl.PROMPT not in capsys.readouterr().out


def test_run_turn_output_goes_through_the_callback(repl, monkeypatch):
    captured = []
    repl.on_output(captured.append)
    monkeypatch.setattr(REPL_MODULE, "Agent", FakeAgent)

    repl.run_turn("hello")

    assert FakeAgent.reply in captured


def test_output_does_not_double_space_text_that_already_ends_in_a_newline(repl, capsys):
    repl._output("already newline-terminated\n")

    assert capsys.readouterr().out == "already newline-terminated\n"


# ---------- Repl: handle_command ---------------------------------------------


@pytest.mark.parametrize("entry", ["/exit", "/quit"])
def test_handle_command_reports_quit(repl, entry):
    assert repl.handle_command(entry) == "quit"


@pytest.mark.parametrize("entry", ["/help", "/clear", "/quiet", "/loud"])
def test_handle_command_reports_a_handled_command(repl, entry):
    assert repl.handle_command(entry) == "command"
    boukensha.loud()  # /quiet is module-global; do not leak it into the next test


def test_handle_command_returns_none_for_anything_else(repl):
    assert repl.handle_command("look at the room") is None
    assert repl.handle_command("/nonsense") is None


def test_handle_command_routes_output_through_the_callback(repl):
    captured = []
    repl.on_output(captured.append)

    repl.handle_command("/clear")

    assert "(conversation history cleared)" in captured


def test_clear_via_handle_command_wipes_history(repl, ctx):
    ctx.add_message("user", "remember this")

    repl.handle_command("/clear")

    assert ctx.messages == []


# ---------- Repl: public accessors the TUI needs -----------------------------


def test_the_repl_exposes_what_a_front_end_needs(repl, ctx, logger):
    assert repl.context is ctx
    assert repl.logger is logger
    assert repl.model == "claude-haiku-4-5"
    assert repl.version == "0.11.0"


# ---------- fmt_tokens -------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "0"), (999, "999"), (1000, "1.0k"), (1500, "1.5k"), (12345, "12.3k"), (None, "0")],
)
def test_fmt_tokens(value, expected):
    assert fmt_tokens(value) == expected


# ---------- Tui: the event state machine -------------------------------------


def test_iteration_updates_the_counter_and_the_action(tui):
    tui._handle_event({"phase": "iteration", "n": 4})

    assert tui._live["iteration"] == 4
    assert tui._live["current_action"] == "Thinking…"


def test_tool_call_names_the_tool_and_counts_it(tui):
    tui._handle_event({"phase": "tool_call", "name": "look"})
    tui._handle_event({"phase": "tool_call", "name": "move"})

    assert tui._live["current_action"] == "Calling tool: move"
    assert tui._live["tool_call_count"] == 2


def test_tool_result_switches_the_action(tui):
    tui._handle_event({"phase": "tool_result"})

    assert tui._live["current_action"] == "Awaiting result…"


def test_response_accumulates_turn_and_session_tokens(tui):
    tui._handle_event({"phase": "response", "usage": {"input_tokens": 100, "output_tokens": 20}})
    tui._handle_event({"phase": "response", "usage": {"input_tokens": 400, "output_tokens": 5}})

    assert tui._live["turn_input_tokens"] == 500
    assert tui._live["turn_output_tokens"] == 25
    assert tui._session_input_tokens == 500
    assert tui._session_output_tokens == 25


def test_a_response_without_usage_is_ignored(tui):
    tui._handle_event({"phase": "response"})

    assert tui._session_input_tokens == 0


def test_turn_complete_stops_the_spinner_and_counts_the_turn(tui):
    tui._live["active"] = True
    tui._turn_running = True

    tui._handle_event({"phase": "turn_complete"})

    assert tui._live["active"] is False
    assert tui._turn_running is False
    assert tui._turn_count == 1


def test_turn_interrupted_is_reported_in_the_conversation(tui):
    tui._live["active"] = True

    tui._handle_event({"phase": "turn_interrupted"})

    assert "[interrupted]" in tui.written
    assert tui._live["active"] is False


def test_turn_error_is_reported_with_its_message(tui):
    tui._handle_event({"phase": "turn_error", "error": "boom"})

    assert "[error] boom" in tui.written
    assert tui._live["active"] is False


def test_output_events_reach_the_conversation(tui):
    tui._handle_event({"phase": "output", "text": "a room"})

    assert tui.written == ["a room"]


def test_an_unrecognised_phase_is_ignored(tui):
    tui._handle_event({"phase": "prompt"})
    tui._handle_event({})

    assert tui.written == []


def test_session_tokens_survive_a_new_turn_but_turn_tokens_reset(tui):
    tui._handle_event({"phase": "response", "usage": {"input_tokens": 100, "output_tokens": 10}})
    tui._live = tui._idle_live()
    tui._handle_event({"phase": "response", "usage": {"input_tokens": 50, "output_tokens": 5}})

    assert tui._live["turn_input_tokens"] == 50
    assert tui._session_input_tokens == 150


# ---------- Tui: the queue drain ---------------------------------------------


def test_draining_applies_every_queued_event_in_order(tui):
    for name in ("look", "move"):
        tui._events.put({"phase": "tool_call", "name": name})
    tui._events.put({"phase": "output", "text": "done"})

    tui._drain_events()

    assert tui._live["tool_call_count"] == 2
    assert tui.written == ["done"]
    assert tui._events.empty()


def test_draining_an_empty_queue_is_a_no_op(tui):
    tui._drain_events()

    assert tui.written == []


def test_the_spinner_advances_and_wraps(tui):
    tui._live["active"] = True
    for _ in range(len(SPINNER_FRAMES)):
        tui._live["spinner_idx"] = (tui._live["spinner_idx"] + 1) % len(SPINNER_FRAMES)

    assert tui._live["spinner_idx"] == 0


# ---------- cancellation -----------------------------------------------------


class SlowAgent:
    """Counts iterations so a test can prove where cancellation lands."""

    started = 0

    def __init__(self, *, context, cancel=None, **_kwargs):
        self._context = context
        self._cancel = cancel

    def run(self):
        SlowAgent.started += 1
        if self._cancel is not None and self._cancel.is_set():
            raise Interrupted("turn cancelled by the user")
        return "finished"


def test_a_set_cancel_event_interrupts_the_turn(repl, monkeypatch):
    SlowAgent.started = 0
    monkeypatch.setattr(REPL_MODULE, "Agent", SlowAgent)
    cancel = threading.Event()
    cancel.set()

    with pytest.raises(Interrupted):
        repl.run_turn("hello", cancel=cancel)


def test_an_unset_cancel_event_lets_the_turn_finish(repl, monkeypatch):
    captured = []
    repl.on_output(captured.append)
    monkeypatch.setattr(REPL_MODULE, "Agent", SlowAgent)

    repl.run_turn("hello", cancel=threading.Event())

    assert "finished" in captured


def test_the_real_agent_checks_cancel_before_the_first_api_call(ctx, logger):
    """The whole point of cooperative cancellation: no request is made once the flag is set."""
    from boukensha.agent import Agent

    class ExplodingClient:
        def call(self, **_kwargs):
            raise AssertionError("the agent made an API call despite being cancelled")

    cancel = threading.Event()
    cancel.set()
    agent = Agent(
        context=ctx,
        registry=Registry(ctx),
        builder=None,
        client=ExplodingClient(),
        logger=logger,
        cancel=cancel,
    )

    with pytest.raises(Interrupted):
        agent.run()

    assert logger.turn_ends == [{"reason": "interrupted", "iterations": 0}]


def test_an_agent_without_a_cancel_event_is_unaffected(ctx, logger):
    """Step 10 behaviour has to survive: cancel is opt-in."""
    from boukensha.agent import Agent

    agent = Agent(context=ctx, registry=Registry(ctx), builder=None, client=None, logger=logger)

    assert agent._cancel is None


# ---------- the app actually running -----------------------------------------


def test_the_app_boots_runs_a_turn_and_exits(repl, monkeypatch):
    """Drives the real Textual app headlessly via its pilot.

    Worth the async plumbing: every other test in this file stubs `_write`, so none of them
    touch Textual itself. This one caught a name collision that made the app unusable —
    `self._context` shadowed Textual's own `App._context`, and `run()` died with
    "'Context' object is not callable" before drawing a frame. Nothing short of booting the app
    would have found it.

    `asyncio.run` inside a sync test keeps this working without a pytest-asyncio dependency.
    """
    import asyncio

    monkeypatch.setattr(REPL_MODULE, "Agent", FakeAgent)
    app = Tui(repl)

    async def drive():
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press(*"look around")
            await pilot.press("enter")
            for _ in range(40):
                await pilot.pause(0.05)
            await pilot.press("ctrl+c")

    asyncio.run(asyncio.wait_for(drive(), 40))

    assert app._turn_count == 1
    assert [m.role for m in repl.context.messages] == ["user", "assistant"]
    assert repl.context.messages[0].content == "look around"
    assert repl.context.messages[1].content == FakeAgent.reply


# ---------- input burst ------------------------------------------------------


def test_a_pasted_burst_is_not_truncated_to_its_first_character(repl, monkeypatch):
    """Ruby needs a patched C extension for this (patches/bubbletea/): its poll_event read up to
    256 bytes, parsed one key event, and discarded the rest, so a paste lost everything after the
    first character. Textual has no such defect and the patch is not ported — this test is here
    precisely because the fix is not inherited.
    """
    burst = "x" * 43
    captured = []
    repl.on_output(captured.append)
    monkeypatch.setattr(REPL_MODULE, "Agent", FakeAgent)
    monkeypatch.setattr("sys.stdin", io.StringIO(f"{burst}\n/exit\n"))

    repl.start()

    assert repl.context.messages[0].content == burst
    assert len(repl.context.messages[0].content) == 43
