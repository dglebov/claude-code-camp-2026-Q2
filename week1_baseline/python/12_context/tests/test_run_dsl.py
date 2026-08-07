"""Tests for `boukensha/run_dsl.py`.

Ruby step 07 ships no specs — see `docs/plans/python_port/07_the_run_dsl.md` §7.1.

`RunDSL` exists to be *small*: it is the entire surface a `run` block can reach, so the tests
assert what it does NOT expose as much as what it does.
"""

import pytest
from boukensha.context import Context
from boukensha.registry import Registry
from boukensha.run_dsl import RunDSL


@pytest.fixture
def context():
    return Context(system="s")


@pytest.fixture
def dsl(context):
    return RunDSL(Registry(context))


def test_tool_registers_on_the_wrapped_registry(dsl, context):
    @dsl.tool("look", description="Look around", parameters={})
    def look():
        return "a corridor"

    assert "look" in context.tools
    assert context.tools["look"].description == "Look around"


def test_the_registered_tool_is_dispatchable(dsl, context):
    @dsl.tool(
        "move",
        description="Move",
        parameters={"direction": {"type": "string", "description": "Which way"}},
    )
    def move(*, direction):
        return f"You move {direction}."

    assert Registry(context).dispatch("move", {"direction": "north"}) == "You move north."


def test_tool_returns_the_undecorated_function(dsl):
    @dsl.tool("look", description="Look around")
    def look():
        return "a corridor"

    assert look() == "a corridor"


def test_parameters_defaults_to_empty(dsl, context):
    @dsl.tool("look", description="Look around")
    def look():
        return "x"

    assert context.tools["look"].parameters == {}


def test_several_tools_can_be_registered(dsl, context):
    @dsl.tool("a", description="A")
    def a():
        return "a"

    @dsl.tool("b", description="B")
    def b():
        return "b"

    assert sorted(context.tools) == ["a", "b"]


def test_the_dsl_exposes_only_tool(dsl):
    """Containment is the point. In Ruby it comes from `instance_eval` rebinding self; here it
    comes from the block only ever receiving this object (plan §5.1)."""
    public = {name for name in dir(dsl) if not name.startswith("_")}

    assert public == {"tool"}
