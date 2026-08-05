"""Tests for the module-level state added in step 06.

Mirrors Ruby's `@config` / `@debug` / `@quiet` module instance variables on `module Boukensha`.
A departure from five steps of dependency injection — see the step-06 plan §8.
"""

import boukensha
import pytest
from boukensha.config import Config


@pytest.fixture(autouse=True)
def reset_module_state(monkeypatch):
    """These are process-wide globals; without a reset they leak between tests (plan §5.1)."""
    monkeypatch.setattr(boukensha, "_config", None)
    monkeypatch.setattr(boukensha, "_debug", False)
    monkeypatch.setattr(boukensha, "_quiet", False)


def test_config_returns_a_config(config_dir):
    assert isinstance(boukensha.config(), Config)


def test_config_is_memoized(config_dir):
    """Ruby's `@config ||= Config.new` — built once, reused for the life of the process."""
    assert boukensha.config() is boukensha.config()


def test_debug_is_off_by_default():
    assert boukensha.is_debug() is False


def test_debug_turns_on_and_stays_on():
    boukensha.debug()

    assert boukensha.is_debug() is True


def test_quiet_is_off_by_default():
    assert boukensha.is_quiet() is False


def test_quiet_and_loud_round_trip():
    """`quiet!`/`loud!`/`quiet?` are declared in Ruby and never consumed — nothing reads the
    flag. Ported for parity and pinned here so a later reader is a deliberate change."""
    boukensha.quiet()
    assert boukensha.is_quiet() is True

    boukensha.loud()
    assert boukensha.is_quiet() is False


def test_the_flags_are_independent():
    boukensha.debug()

    assert boukensha.is_debug() is True
    assert boukensha.is_quiet() is False
