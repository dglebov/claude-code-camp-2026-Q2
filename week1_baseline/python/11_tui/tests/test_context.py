import pytest
from boukensha.context import Context
from boukensha.message import Message
from boukensha.tasks import Player
from boukensha.tool import Tool


@pytest.fixture
def ctx():
    return Context(task=Player)


# ---------- construction -----------------------------------------------------


def test_task_is_keyword_only():
    """Ruby's `initialize(task:, system: nil)` has no positional form."""
    with pytest.raises(TypeError):
        Context(Player)


def test_task_is_required():
    with pytest.raises(TypeError):
        Context()


def test_system_defaults_to_none(ctx):
    assert ctx.system is None


def test_starts_empty(ctx):
    assert ctx.messages == []
    assert ctx.tools == {}
    assert ctx.turn_count == 0
    assert ctx.tool_count == 0


def test_collections_are_not_shared_between_instances():
    first = Context(task=Player)
    second = Context(task=Player)

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

    assert str(ctx) == "#<Context task=player turns=2 tools=1>"


def test_str_on_empty_context(ctx):
    assert str(ctx) == "#<Context task=player turns=0 tools=0>"


def test_str_with_no_task_renders_empty_not_none():
    """Ruby's `task&.task_name` yields nil, which interpolates as an empty string."""
    assert str(Context(task=None)) == "#<Context task= turns=0 tools=0>"


def test_repr_matches_str(ctx):
    assert repr(ctx) == str(ctx)


def test_task_holds_the_class_not_an_instance(ctx):
    assert ctx.task is Player
    assert ctx.task.task_name() == "player"


# ---------- clear_messages (new in step 08) ---------------------------------


def test_clear_messages_drops_history(ctx):
    ctx.add_message("user", "hello")
    ctx.add_message("assistant", "hi")
    assert ctx.turn_count == 2

    ctx.clear_messages()

    assert ctx.turn_count == 0
    assert ctx.messages == []


def test_clear_messages_keeps_tools_and_system():
    context = Context(task=Player, system="You are a MUD player assistant.")
    context.register_tool(Tool("look", "Look around", {}, lambda: "a room"))
    context.add_message("user", "hello")

    context.clear_messages()

    assert context.tool_count == 1
    assert context.system == "You are a MUD player assistant."
    assert context.task is Player


def test_clear_messages_is_idempotent(ctx):
    ctx.clear_messages()
    ctx.clear_messages()
    assert ctx.turn_count == 0


def test_messages_can_be_added_again_after_clearing(ctx):
    ctx.add_message("user", "first")
    ctx.clear_messages()
    ctx.add_message("user", "second")

    assert [m.content for m in ctx.messages] == ["second"]
