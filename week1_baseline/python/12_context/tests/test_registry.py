import pytest
from boukensha.context import Context
from boukensha.errors import UnknownToolError
from boukensha.registry import Registry
from boukensha.tool import Tool


@pytest.fixture
def ctx():
    return Context()


@pytest.fixture
def registry(ctx):
    return Registry(ctx)


# ---------- registration -----------------------------------------------------


def test_tool_returns_a_decorator_that_registers(registry, ctx):
    @registry.tool("move", description="Move somewhere", parameters={"direction": {"type": "string"}})
    def move(*, direction):
        return f"moved {direction}"

    assert ctx.tool_count == 1
    assert isinstance(ctx.tools["move"], Tool)


def test_decorator_returns_the_original_function(registry):
    @registry.tool("shout", description="Shout", parameters={"message": {"type": "string"}})
    def shout(*, message):
        return message.upper()

    assert callable(shout)
    assert shout(message="hi") == "HI"


def test_registered_tool_carries_description_parameters_and_block(registry, ctx):
    parameters = {"direction": {"type": "string"}}

    @registry.tool("move", description="Move somewhere", parameters=parameters)
    def move(*, direction):
        return f"moved {direction}"

    tool = ctx.tools["move"]
    assert tool.name == "move"
    assert tool.description == "Move somewhere"
    assert tool.parameters == parameters
    assert tool.block is move


def test_parameters_default_to_empty(registry, ctx):
    @registry.tool("look", description="Look around")
    def look():
        return "a torch-lit corridor"

    assert ctx.tools["look"].parameters == {}


def test_default_parameters_are_not_shared_between_tools(registry, ctx):
    """Ruby's `parameters: {}` allocates per call; a Python default would be shared."""

    @registry.tool("look", description="Look around")
    def look():
        return "..."

    @registry.tool("wait", description="Wait a turn")
    def wait():
        return "..."

    ctx.tools["look"].parameters["direction"] = {"type": "string"}
    assert ctx.tools["wait"].parameters == {}


def test_name_is_coerced_to_string(registry, ctx):
    """Ruby calls `name.to_s`, so a non-string name still keys the hash by its string form."""

    @registry.tool(1, description="Numbered")
    def numbered():
        return "..."

    assert list(ctx.tools) == ["1"]


def test_registering_the_same_name_replaces(registry, ctx):
    @registry.tool("move", description="First")
    def first():
        return "first"

    @registry.tool("move", description="Second")
    def second():
        return "second"

    assert ctx.tool_count == 1
    assert ctx.tools["move"].description == "Second"


def test_registration_order_is_preserved(registry, ctx):
    @registry.tool("move", description="Move")
    def move():
        return "..."

    @registry.tool("shout", description="Shout")
    def shout():
        return "..."

    assert list(ctx.tools) == ["move", "shout"]


def test_registry_writes_through_to_the_context_it_was_given(ctx):
    """Tools live on the Context; the Registry only holds a reference to it."""
    other = Context()

    @Registry(ctx).tool("move", description="Move")
    def move():
        return "..."

    assert ctx.tool_count == 1
    assert other.tool_count == 0


# ---------- dispatch ---------------------------------------------------------


def test_dispatch_calls_the_block_and_returns_its_value(registry):
    @registry.tool("move", description="Move", parameters={"direction": {"type": "string"}})
    def move(*, direction):
        return f"You move {direction} into a torch-lit corridor."

    result = registry.dispatch("move", {"direction": "north"})
    assert result == "You move north into a torch-lit corridor."


def test_dispatch_passes_string_keys_as_keywords(registry):
    """Ruby needs `transform_keys(&:to_sym)` here; Python keyword arguments are already strings."""
    seen = {}

    @registry.tool("shout", description="Shout", parameters={"message": {"type": "string"}})
    def shout(*, message):
        seen["message"] = message
        return message.upper()

    assert registry.dispatch("shout", {"message": "dragon spotted"}) == "DRAGON SPOTTED"
    assert seen == {"message": "dragon spotted"}


def test_dispatch_with_no_args_at_all(registry):
    @registry.tool("look", description="Look around")
    def look():
        return "a torch-lit corridor"

    assert registry.dispatch("look") == "a torch-lit corridor"


def test_dispatch_accepts_a_non_string_name(registry):
    @registry.tool("1", description="Numbered")
    def numbered():
        return "one"

    assert registry.dispatch(1) == "one"


def test_dispatch_unknown_tool_raises(registry):
    with pytest.raises(UnknownToolError) as excinfo:
        registry.dispatch("flee")

    assert str(excinfo.value) == "No tool registered as 'flee'"


def test_unknown_tool_error_is_a_plain_exception(registry):
    """Ruby subclasses StandardError, so a bare `rescue` catches it."""
    with pytest.raises(Exception):  # noqa: B017 — the point is that Exception is broad enough
        registry.dispatch("flee")


def test_dispatch_with_a_missing_argument_raises_type_error_not_unknown_tool(registry):
    """The error boundary is about the tool *name*; bad arguments fail in the block itself."""

    @registry.tool("move", description="Move", parameters={"direction": {"type": "string"}})
    def move(*, direction):
        return f"moved {direction}"

    with pytest.raises(TypeError):
        registry.dispatch("move")


def test_dispatch_with_an_unexpected_argument_raises_type_error(registry):
    @registry.tool("look", description="Look around")
    def look():
        return "..."

    with pytest.raises(TypeError):
        registry.dispatch("look", {"direction": "north"})


# ---------- registered() and required= (new in step 10) ----------------------


def test_registered_is_false_before_and_true_after(registry, ctx):
    assert registry.registered("look") is False

    @registry.tool("look", description="d", parameters={})
    def look():
        return "a room"

    assert registry.registered("look") is True


def test_registered_coerces_the_name(registry):
    @registry.tool("look", description="d", parameters={})
    def look():
        return "a room"

    assert registry.registered("look") is True


def test_required_reaches_the_tool(registry, ctx):
    @registry.tool("t", description="d", parameters={"a": {}, "b": {}}, required=["a"])
    def t(**kwargs):
        return ""

    assert ctx.tools["t"].required_keys() == ["a"]


def test_the_call_form_registers_a_plain_callable(registry, ctx):
    """MCP tools are discovered at runtime and have no `def` to decorate (plan §5.3)."""
    registry.tool("dynamic", description="d", parameters={})(lambda **kw: "ok")

    assert ctx.tools["dynamic"].block() == "ok"
