"""Tests for step 12's context-window accounting and compaction.

Ruby step 12 ships no specs — see `docs/plans/python_port/12_context.md` §7.

Kept separate from `test_context.py` so the step-11 behaviour it covers stays diffable against
step 11's copy of that file.

The distinction under test throughout: `current_tokens` is **window pressure** (does it fit?) and
`turn_tokens` is **spend** (what did it cost?). One can be tiny while the other is huge.
"""

import pytest
from boukensha.context import Context
from boukensha.tool import Tool


def ctx(**kwargs):
    return Context(system="t", **kwargs)


# ---------- usage arithmetic -------------------------------------------------


def test_usage_starts_at_zero():
    c = ctx(context_window=1000)
    assert c.usage_fraction() == 0.0
    assert c.usage_pct() == 0


def test_usage_tracks_update_tokens():
    c = ctx(context_window=1000)
    c.update_tokens(250)
    assert c.usage_fraction() == 0.25
    assert c.usage_pct() == 25


def test_a_zero_width_window_does_not_divide_by_zero():
    c = ctx(context_window=0)
    c.update_tokens(500)
    assert c.usage_fraction() == 0.0
    assert c.usage_pct() == 0


def test_update_tokens_coerces_none_to_zero():
    c = ctx(context_window=1000)
    c.update_tokens(None)
    assert c.current_tokens == 0


def test_usage_pct_rounds_half_up_like_ruby():
    """Ruby's Float#round goes half away from zero; Python's round() is banker's rounding.

        Ruby:   (0.5).round  => 1
        Python: round(0.5)   => 0

    70.5% is exactly the boundary where the TUI switches to its warning colour, so the two trees
    would disagree on the colour of the same session. context.py uses floor(x + 0.5) to match.
    """
    c = ctx(context_window=10_000)
    c.update_tokens(7050)  # 70.5%
    assert c.usage_pct() == 71

    c.update_tokens(6050)  # 60.5%
    assert c.usage_pct() == 61


# ---------- turn spend -------------------------------------------------------


def test_turn_tokens_accumulate_across_calls():
    c = ctx()
    c.add_turn_tokens(100, 20)
    c.add_turn_tokens(50, 5)
    assert c.turn_tokens == 175


def test_turn_tokens_reset():
    c = ctx()
    c.add_turn_tokens(100, 20)
    c.reset_turn_tokens()
    assert c.turn_tokens == 0


def test_turn_tokens_tolerate_none():
    c = ctx()
    c.add_turn_tokens(None, None)
    assert c.turn_tokens == 0


def test_spend_and_window_pressure_are_independent():
    """The whole reason there are two counters."""
    c = ctx(context_window=1_000_000)
    for _ in range(10):
        c.add_turn_tokens(1000, 500)
        c.update_tokens(1000)

    assert c.turn_tokens == 15_000  # a lot spent
    assert c.usage_pct() == 0  # window barely touched


# ---------- the compaction trigger -------------------------------------------


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [(8_499, False), (8_500, True), (9_000, True)],
)
def test_needs_compaction_at_the_threshold(tokens, expected):
    c = ctx(context_window=10_000, compaction_threshold=0.85)
    c.update_tokens(tokens)
    assert c.needs_compaction() is expected


def test_an_explicit_threshold_overrides_the_configured_one():
    c = ctx(context_window=10_000, compaction_threshold=0.85)
    c.update_tokens(5_000)
    assert c.needs_compaction() is False
    assert c.needs_compaction(threshold=0.4) is True


# ---------- compaction arithmetic --------------------------------------------


def messages(n):
    c = ctx()
    for i in range(n):
        c.add_message("user", f"m{i}")
    return c


def test_compaction_drops_the_oldest_40_percent():
    c = messages(10)
    dropped = c.compact_messages()

    assert dropped == 4
    assert len(c.messages) == 6
    assert c.messages[0].content == "m4"


def test_compaction_rounds_the_drop_count_up():
    """Ruby is `(size * 0.40).ceil` — 5 messages means 2 dropped, not 2.0 truncated to 2 by luck."""
    c = messages(5)
    assert c.compact_messages() == 2


def test_compaction_keeps_at_least_two_messages():
    c = messages(3)
    dropped = c.compact_messages()

    assert dropped == 1
    assert len(c.messages) == 2


@pytest.mark.parametrize("size", [0, 1, 2])
def test_compaction_never_drops_below_the_floor(size):
    """`size - 2` goes negative here; the final max(_, 0) is what stops a negative slice."""
    c = messages(size)
    dropped = c.compact_messages()

    assert dropped == 0
    assert len(c.messages) == size


def test_compaction_resets_the_known_window_usage():
    """The dropped messages accounted for those tokens; the next response supplies the real figure."""
    c = messages(10)
    c.update_tokens(9_000)
    c.compact_messages()

    assert c.current_tokens == 0


def test_compaction_keeps_tools_and_system():
    c = messages(10)
    c.register_tool(Tool("look", "Look around", {}, lambda: "a room"))
    c.compact_messages()

    assert c.tool_count == 1
    assert c.system == "t"
