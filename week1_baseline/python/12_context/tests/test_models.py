"""Tests for `boukensha/models.py`.

Ruby step 12 ships no specs — see `docs/plans/python_port/12_context.md` §7.

The table is deliberately small and the lookup deliberately forgiving: an unrecognised model must
degrade to a conservative window rather than raising at startup or, worse, assuming a huge one and
letting the conversation run past what the provider accepts.
"""

import pytest
from boukensha import models


def test_a_known_model_returns_its_window():
    assert models.context_window("claude-haiku-4-5") == 200_000


def test_every_table_entry_is_reachable():
    for name, entry in models.TABLE.items():
        assert models.context_window(name) == entry["context_window"]


def test_an_unknown_model_falls_back_to_the_conservative_default():
    assert models.context_window("gpt-9-imaginary") == models.DEFAULT_CONTEXT_WINDOW
    assert models.DEFAULT_CONTEXT_WINDOW == 32_000


@pytest.mark.parametrize("value", [None, "", 0])
def test_a_missing_model_id_does_not_raise(value):
    """Ruby coerces with `model.to_s`, so nil misses the table rather than blowing up. An
    unconfigured model must degrade, not crash the run before it starts."""
    assert models.context_window(value) == models.DEFAULT_CONTEXT_WINDOW


def test_the_default_is_smaller_than_every_real_window():
    """A fallback larger than a real model's window would defeat the point."""
    assert all(e["context_window"] > models.DEFAULT_CONTEXT_WINDOW for e in models.TABLE.values())
