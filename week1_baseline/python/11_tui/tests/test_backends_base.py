from typing import ClassVar

import pytest
from boukensha.backends.base import Base
from boukensha.errors import UnsupportedModelError


class Priced(Base):
    MODELS: ClassVar[dict] = {
        "cheap": {
            "context_window": 1000,
            "cost_per_million": {"input": 1.0, "output": 5.0},
            "usage_unit": "tokens",
        },
        "free": {
            "context_window": 2000,
            "cost_per_million": {"input": 0.0, "output": 0.0},
            "usage_unit": "local_compute",
        },
        "unpriced": {
            "context_window": 3000,
            "cost_per_million": {"input": None, "output": None},
            "usage_unit": "ollama_cloud_usage",
            "usage_level": "high",
        },
        "incomplete": {
            "cost_per_million": {"input": 1.0, "output": 1.0},
            "usage_unit": "tokens",
        },
    }

    def __init__(self, model):
        self._configure_model(model)


# ---------- the model table --------------------------------------------------


def test_base_has_no_models():
    """Ruby rescues the NameError from `const_get(:MODELS)` on the base class."""
    with pytest.raises(NotImplementedError):
        Base.models()


def test_validate_model_returns_the_name():
    assert Priced.validate_model("cheap") == "cheap"


def test_validate_model_coerces_to_string():
    class Numbered(Base):
        MODELS: ClassVar[dict] = {
            "1": {"context_window": 1, "cost_per_million": {"input": 0.0, "output": 0.0}, "usage_unit": "tokens"}
        }

    assert Numbered.validate_model(1) == "1"


def test_unknown_model_raises_with_the_ruby_message():
    """Ruby's `model.inspect` renders double quotes; repr() would render single ones."""
    with pytest.raises(UnsupportedModelError) as excinfo:
        Priced.validate_model("nope")

    assert str(excinfo.value) == (
        'Boukensha::Backends::Priced does not support model "nope". '
        "Supported models: cheap, free, incomplete, unpriced"
    )


def test_constructing_with_an_unknown_model_raises():
    with pytest.raises(UnsupportedModelError):
        Priced("nope")


# ---------- model metadata ---------------------------------------------------


def test_model_and_model_info():
    backend = Priced("cheap")

    assert backend.model == "cheap"
    assert backend.model_info is Priced.MODELS["cheap"]


def test_context_window_and_usage_unit():
    backend = Priced("free")

    assert backend.context_window == 2000
    assert backend.usage_unit == "local_compute"


def test_missing_context_window_raises():
    """Ruby uses `fetch`, which raises rather than returning nil."""
    with pytest.raises(KeyError):
        _ = Priced("incomplete").context_window


def test_usage_level_is_none_when_absent():
    """Ruby's `model_info[:usage_level]` yields nil — unlike `fetch`, it does not raise."""
    assert Priced("cheap").usage_level is None
    assert Priced("unpriced").usage_level == "high"


# ---------- estimate_cost ----------------------------------------------------


def test_estimate_cost_computes_from_the_table():
    backend = Priced("cheap")

    assert backend.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000) == 6.0
    assert backend.estimate_cost(input_tokens=2000, output_tokens=500) == pytest.approx(0.0045)


def test_estimate_cost_is_zero_not_none_for_a_free_model():
    """0.0 is truthy in Ruby and falsy in Python — the trap this step turns on."""
    assert Priced("free").estimate_cost(input_tokens=1000, output_tokens=1000) == 0.0


def test_estimate_cost_is_none_when_pricing_is_unknown():
    assert Priced("unpriced").estimate_cost(input_tokens=1000, output_tokens=1000) is None


def test_zero_tokens_costs_nothing():
    assert Priced("cheap").estimate_cost(input_tokens=0, output_tokens=0) == 0.0
