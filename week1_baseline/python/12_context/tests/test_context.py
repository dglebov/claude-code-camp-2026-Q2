import pytest
from boukensha.context import Context
from boukensha.message import Message
from boukensha.tool import Tool


@pytest.fixture
def ctx():
    return Context()


# ---------- construction -----------------------------------------------------


def test_system_defaults_to_none(ctx):
    assert ctx.system is None


def test_starts_empty(ctx):
    assert ctx.messages == []
    assert ctx.tools == {}
    assert ctx.turn_count == 0
    assert ctx.tool_count == 0


def test_collections_are_not_shared_between_instances():
    first = Context()
    second = Context()

    first.add_message("user", "hi")
    first.register_tool(Tool("look", "Look around", {}))

    assert second.messages == []
    assert second.tools == {}


# ---------- tools ------------------------------------------------------------


def test_register_tool_keys_by_tool_name(ctx):
    tool = Tool("move", "Move somewhere", {})
    ctx.register_tool(tool)

    assert ctx.tools == {"move": tool}
    assert ctx.tool_count == 1


def test_registering_the_same_name_replaces(ctx):
    ctx.register_tool(Tool("move", "First", {}))
    ctx.register_tool(Tool("move", "Second", {}))

    assert ctx.tool_count == 1
    assert ctx.tools["move"].description == "Second"


# ---------- messages ---------------------------------------------------------


def test_add_message_appends_in_order(ctx):
    ctx.add_message("user", "first")
    ctx.add_message("assistant", "second")

    assert [m.content for m in ctx.messages] == ["first", "second"]
    assert ctx.turn_count == 2


def test_add_message_builds_a_message(ctx):
    ctx.add_message("user", "hi")

    assert ctx.messages[0] == Message("user", "hi", None)


def test_add_message_threads_tool_use_id(ctx):
    ctx.add_message("tool_result", "output", tool_use_id="toolu_01X")

    assert ctx.messages[0].tool_use_id == "toolu_01X"


# ---------- __str__ ----------------------------------------------------------


def test_str_matches_ruby_format(ctx):
    ctx.register_tool(Tool("move", "Move somewhere", {}))
    ctx.add_message("user", "hi")
    ctx.add_message("assistant", "there")

    assert str(ctx) == "#<Context turns=2 tools=1 window=200000 current=0>"


def test_str_on_empty_context(ctx):
    assert str(ctx) == "#<Context turns=0 tools=0 window=200000 current=0>"


def test_repr_matches_str(ctx):
    assert repr(ctx) == str(ctx)


def test_clear_messages_drops_history(ctx):
    ctx.add_message("user", "hello")
    ctx.add_message("assistant", "hi")
    assert ctx.turn_count == 2

    ctx.clear_messages()

    assert ctx.turn_count == 0
    assert ctx.messages == []


def test_clear_messages_keeps_tools_and_system():
    context = Context(system="You are a MUD player assistant.")
    context.register_tool(Tool("look", "Look around", {}, lambda: "a room"))
    context.add_message("user", "hello")

    context.clear_messages()

    assert context.tool_count == 1
    assert context.system == "You are a MUD player assistant."
    # New in step 12: clearing history also zeroes the known window usage, since the messages
    # those tokens accounted for are gone.
    assert context.current_tokens == 0


def test_clear_messages_is_idempotent(ctx):
    ctx.clear_messages()
    ctx.clear_messages()
    assert ctx.turn_count == 0


def test_messages_can_be_added_again_after_clearing(ctx):
    ctx.add_message("user", "first")
    ctx.clear_messages()
    ctx.add_message("user", "second")

    assert [m.content for m in ctx.messages] == ["second"]
