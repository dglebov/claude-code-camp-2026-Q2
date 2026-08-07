"""Tests for `boukensha/repl.py` and the `boukensha.repl` entry point.

Ruby step 08 ships no specs — see `docs/plans/python_port/10_standard_tool_library.md` §7.1.

Nothing here touches the network. The REPL builds its Agent per turn, so patching `Agent` in the
repl module is the only seam needed. That patch has to go through
`importlib.import_module("boukensha.repl")`: `def repl(...)` in `__init__.py` rebinds the
`boukensha.repl` attribute from the module to the function, so the attribute path reaches the
function rather than the module (see the repl.py docstring).
"""

import importlib
import io

import boukensha
import pytest
from boukensha.context import Context
from boukensha.registry import Registry
from boukensha.repl import Repl

SYSTEM = "You are a MUD player assistant."
REPL_MODULE = importlib.import_module("boukensha.repl")


class FakeAgent:
    """Stands in for Agent so no API call happens. Mirrors what the real one does as of step 08:
    append the reply to the context, then return it."""

    reply = "a fake reply"

    def __init__(self, *, context, **_kwargs):
        self._context = context

    def run(self):
        self._context.add_message("assistant", self.reply)
        return self.reply


class ExplodingAgent:
    def __init__(self, *, error, **_kwargs):
        self._error = error

    def run(self):
        raise self._error


class FakeLogger:
    def __init__(self):
        self.turns = []
        self.closed = False

    def turn(self, *, n):
        self.turns.append(n)

    def close(self):
        self.closed = True


@pytest.fixture
def ctx():
    return Context(system=SYSTEM)


@pytest.fixture
def logger():
    return FakeLogger()


@pytest.fixture
def build(ctx, logger):
    def make(**overrides):
        kwargs = {
            "context": ctx,
            "registry": Registry(ctx),
            "builder": None,
            "client": None,
            "logger": logger,
            "config_dir": None,
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "version": "0.8.0",
            "api_key": "sk-test",
        }
        kwargs.update(overrides)
        return Repl(**kwargs)

    return make


@pytest.fixture
def drive(monkeypatch):
    """Feed keystrokes to a REPL as stdin and run it to completion."""

    def run(repl, keystrokes, agent=FakeAgent):
        monkeypatch.setattr("sys.stdin", io.StringIO(keystrokes))
        monkeypatch.setattr(REPL_MODULE, "Agent", agent)
        repl.start()

    return run


# ---------- leaving the loop -------------------------------------------------


def test_exit_stops_the_loop_and_says_goodbye(build, drive, capsys):
    drive(build(), "/exit\n")

    assert "Goodbye." in capsys.readouterr().out


def test_quit_is_an_alias_for_exit(build, drive, capsys):
    drive(build(), "/quit\n")

    assert "Goodbye." in capsys.readouterr().out


def test_eof_leaves_the_loop_without_a_goodbye(build, drive, capsys):
    """Ruby's `break unless input` — Ctrl-D exits silently, unlike /exit."""
    drive(build(), "")

    assert "Goodbye." not in capsys.readouterr().out


def test_input_after_exit_is_never_read(build, drive, logger):
    drive(build(), "/exit\nlook around\n")

    assert logger.turns == []


# ---------- built-in commands ------------------------------------------------


def test_help_lists_every_command(build, drive, capsys):
    drive(build(), "/help\n/exit\n")

    out = capsys.readouterr().out
    for command in ("/quiet", "/loud", "/clear", "/exit", "/help"):
        assert command in out


def test_a_command_never_reaches_the_agent(build, drive, ctx, logger):
    drive(build(), "/help\n/exit\n")

    assert logger.turns == []
    assert ctx.turn_count == 0


def test_blank_and_whitespace_only_input_is_skipped(build, drive, ctx, logger):
    drive(build(), "\n   \n\t\n/exit\n")

    assert logger.turns == []
    assert ctx.turn_count == 0


def test_input_is_stripped_before_dispatch(build, drive, capsys):
    """`  /exit  ` is the exit command, matching Ruby's chomp.strip."""
    drive(build(), "  /exit  \n")

    assert "Goodbye." in capsys.readouterr().out


def test_quiet_and_loud_toggle_module_state(build, drive, capsys):
    try:
        drive(build(), "/quiet\n/exit\n")
        assert boukensha.is_quiet() is True

        drive(build(), "/loud\n/exit\n")
        assert boukensha.is_quiet() is False
    finally:
        boukensha.loud()


def test_quiet_and_loud_announce_themselves(build, drive, capsys):
    try:
        drive(build(), "/quiet\n/loud\n/exit\n")
        out = capsys.readouterr().out
        assert "(logging suppressed — type /loud to re-enable)" in out
        assert "(logging enabled)" in out
    finally:
        boukensha.loud()


def test_clear_wipes_history_but_keeps_tools(build, drive, ctx, capsys):
    registry = Registry(ctx)

    @registry.tool("look", description="Look around", parameters={})
    def look():
        return "a room"

    drive(build(registry=registry), "first\n/clear\n/exit\n")

    assert ctx.turn_count == 0
    assert ctx.tool_count == 1
    assert "(conversation history cleared)" in capsys.readouterr().out


def test_clear_resets_the_turn_counter(build, drive, logger):
    drive(build(), "first\n/clear\nsecond\n/exit\n")

    assert logger.turns == [1, 1]


# ---------- running a turn ---------------------------------------------------


def test_a_normal_line_runs_a_turn_and_prints_the_reply(build, drive, ctx, logger, capsys):
    drive(build(), "look around\n/exit\n")

    assert FakeAgent.reply in capsys.readouterr().out
    assert logger.turns == [1]
    assert ctx.messages[0].role == "user"
    assert ctx.messages[0].content == "look around"


def test_history_accumulates_across_turns(build, drive, ctx, logger):
    """The whole point of the step: turn 2 sees turn 1."""
    drive(build(), "first\nsecond\n/exit\n")

    assert logger.turns == [1, 2]
    assert [m.content for m in ctx.messages] == [
        "first",
        FakeAgent.reply,
        "second",
        FakeAgent.reply,
    ]


def test_a_command_between_turns_does_not_advance_the_counter(build, drive, logger):
    drive(build(), "first\n/help\nsecond\n/exit\n")

    assert logger.turns == [1, 2]


# ---------- errors do not kill the session -----------------------------------


def test_an_api_error_is_reported_and_the_loop_survives(build, drive, capsys):
    def agent(**kwargs):
        return ExplodingAgent(error=boukensha.ApiError("boom"), **kwargs)

    drive(build(), "first\n/exit\n", agent=agent)

    out = capsys.readouterr().out
    assert "[error] API call failed: boom" in out
    assert "Goodbye." in out


def test_a_loop_error_is_reported_and_the_loop_survives(build, drive, capsys):
    from boukensha.errors import LoopError

    def agent(**kwargs):
        return ExplodingAgent(error=LoopError("ran away"), **kwargs)

    drive(build(), "first\n/exit\n", agent=agent)

    out = capsys.readouterr().out
    assert "[error] ran away" in out
    assert "Goodbye." in out


def test_a_failed_turn_still_counts_as_a_turn(build, drive, logger):
    def agent(**kwargs):
        return ExplodingAgent(error=boukensha.ApiError("boom"), **kwargs)

    drive(build(), "first\nsecond\n/exit\n", agent=agent)

    assert logger.turns == [1, 2]


# ---------- the banner -------------------------------------------------------


def test_the_banner_reports_a_present_api_key(build, drive, capsys):
    drive(build(), "/exit\n")

    assert "✓ API key set" in capsys.readouterr().out


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_the_banner_reports_a_missing_api_key(build, drive, capsys, api_key):
    drive(build(api_key=api_key), "/exit\n")

    assert "✗ API key not set" in capsys.readouterr().out


def test_the_banner_reports_a_missing_config_dir(build, drive, capsys):
    drive(build(config_dir="/nope/not/here"), "/exit\n")

    assert "✗ directory not found" in capsys.readouterr().out


def test_the_banner_shows_an_existing_config_dir_plainly(build, drive, capsys, tmp_path):
    drive(build(config_dir=str(tmp_path)), "/exit\n")

    out = capsys.readouterr().out
    assert str(tmp_path) in out
    assert "✗ directory not found" not in out


def test_the_banner_carries_the_version_and_provider(build, drive, capsys):
    drive(build(), "/exit\n")

    out = capsys.readouterr().out
    assert "BOUKENSHA MUD Assistant (v0.8.0)" in out
    assert "anthropic (claude-haiku-4-5)" in out


def test_a_long_version_does_not_blow_up_the_banner(build, drive, capsys):
    """Ruby's `" " * (9 - ver.length)` raises on a longer version; max(0, …) keeps it printing."""
    drive(build(version="10.20.30-rc1"), "/exit\n")

    assert "BOUKENSHA MUD Assistant (v10.20.30-rc1)" in capsys.readouterr().out


# ---------- the boukensha.repl entry point -----------------------------------


SETTINGS = "tasks:\n  player:\n    provider: anthropic\n    model: claude-haiku-4-5\n"


@pytest.fixture
def settings(config_dir):
    (config_dir / "settings.yaml").write_text(SETTINGS, encoding="utf-8")
    (config_dir / "sessions").mkdir()
    return config_dir


def test_repl_wires_a_repl_from_config_and_starts_it(monkeypatch, settings):
    seen = {}

    class FakeRepl:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def start(self):
            seen["started"] = True

    monkeypatch.setattr(boukensha, "Repl", FakeRepl)
    boukensha.repl()

    assert seen["started"] is True
    assert seen["model"] == "claude-haiku-4-5"
    assert seen["provider"] == "anthropic"
    assert seen["version"] == boukensha.VERSION
    assert seen["config_dir"] == str(settings)


def test_repl_registers_tools_from_the_block(monkeypatch, settings):
    seen = {}

    class FakeRepl:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def start(self):
            pass

    def register(dsl):
        @dsl.tool("look", description="Look around", parameters={})
        def look():
            return "a room"

    monkeypatch.setattr(boukensha, "Repl", FakeRepl)
    boukensha.repl(block=register, working_dir=False)

    assert seen["context"].tool_count == 1


def test_repl_takes_no_task_argument(monkeypatch, settings):
    with pytest.raises(TypeError):
        boukensha.repl(task="not allowed")


def test_repl_starts_with_an_empty_transcript(monkeypatch, settings):
    seen = {}

    class FakeRepl:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def start(self):
            pass

    monkeypatch.setattr(boukensha, "Repl", FakeRepl)
    boukensha.repl()

    assert seen["context"].turn_count == 0


def test_repl_rejects_an_unknown_backend(monkeypatch, settings):
    with pytest.raises(ValueError, match="Unknown backend"):
        boukensha.repl(backend="nope")


def test_repl_closes_the_logger_on_the_way_out(monkeypatch, settings):
    closed = []

    class FakeRepl:
        def __init__(self, **kwargs):
            self._logger = kwargs["logger"]

        def start(self):
            pass

    monkeypatch.setattr(boukensha, "Repl", FakeRepl)
    real_close = boukensha.Logger.close
    monkeypatch.setattr(
        boukensha.Logger, "close", lambda self: (closed.append(True), real_close(self))[1]
    )
    boukensha.repl()

    assert closed == [True]


def test_ctrl_c_leaves_the_repl_gracefully(monkeypatch, settings, capsys):
    class InterruptingRepl:
        def __init__(self, **kwargs):
            pass

        def start(self):
            raise KeyboardInterrupt

    monkeypatch.setattr(boukensha, "Repl", InterruptingRepl)
    boukensha.repl()  # must not propagate

    assert "Interrupted." in capsys.readouterr().out
