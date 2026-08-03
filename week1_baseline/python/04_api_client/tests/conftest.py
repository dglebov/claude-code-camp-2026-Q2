"""Fixtures shared by the backend tests.

Kept here rather than in the iteration-root conftest.py so that file stays byte-identical to the
one every other step ships.
"""

import pytest
from boukensha.context import Context
from boukensha.registry import Registry
from boukensha.tasks import Player

SYSTEM = "You are a MUD player assistant."
LOOK_RESULT = "A damp stone corridor stretches north."


@pytest.fixture
def context():
    """The shape the example builds: one tool with no parameters, one with, and three messages
    including a tool result."""
    ctx = Context(task=Player, system=SYSTEM)
    registry = Registry(ctx)

    @registry.tool("look", description="Look around the current room for details", parameters={})
    def look():
        return LOOK_RESULT

    @registry.tool(
        "move",
        description="Move the player in a direction",
        parameters={"direction": {"type": "string", "description": "The direction to move"}},
    )
    def move(*, direction):
        return f"You move {direction}."

    ctx.add_message("user", "What's around me?")
    ctx.add_message("assistant", "Let me take a look around first.")
    ctx.add_message("tool_result", LOOK_RESULT, tool_use_id="toolu_01X")
    return ctx


@pytest.fixture
def empty_context():
    return Context(task=Player, system=SYSTEM)
