from boukensha.tool import Tool, ruby_symbol_list

MOVE_DESCRIPTION = "Move the player in a direction (north, south, east, west, up, down)"
# Verified against the Ruby runtime: `description.to_s[0..40]` yields these 41 characters.
MOVE_DESCRIPTION_TRUNCATED = "Move the player in a direction (north, so"


def build_move_tool():
    return Tool(
        "move",
        MOVE_DESCRIPTION,
        {"direction": {"type": "string", "description": "The direction to move"}},
        lambda direction: f"You move {direction} into a torch-lit corridor.",
    )


# ---------- symbol list rendering --------------------------------------------


def test_symbol_list_single_key():
    assert ruby_symbol_list(["direction"]) == "[:direction]"


def test_symbol_list_multiple_keys():
    assert ruby_symbol_list(["target", "weapon"]) == "[:target, :weapon]"


def test_symbol_list_empty():
    assert ruby_symbol_list([]) == "[]"


# ---------- __str__ ----------------------------------------------------------


def test_str_matches_ruby_format():
    expected = f"#<Tool name=move description={MOVE_DESCRIPTION_TRUNCATED} params=[:direction]>"

    assert str(build_move_tool()) == expected


def test_description_truncated_at_exactly_41_characters():
    """Ruby's [0..40] is an inclusive range. A naive [:40] silently drops a character."""
    tool = Tool("x", "a" * 100, {})

    assert "a" * 41 in str(tool)
    assert "a" * 42 not in str(tool)


def test_short_description_is_not_padded_or_truncated():
    tool = Tool("look", "Look around", {})

    assert str(tool) == "#<Tool name=look description=Look around params=[]>"


def test_empty_parameters_render_as_empty_list():
    assert "params=[]" in str(Tool("look", "Look around", {}))


def test_two_parameters_render_in_order():
    tool = Tool("attack", "Attack a target", {"target": {}, "weapon": {}})

    assert "params=[:target, :weapon]" in str(tool)


def test_none_parameters_render_as_empty_list_rather_than_raising():
    assert "params=[]" in str(Tool("look", "Look around", None))


def test_none_description_renders_empty_not_none():
    tool = Tool("look", None, {})

    assert str(tool) == "#<Tool name=look description= params=[]>"


def test_repr_matches_str():
    tool = build_move_tool()

    assert repr(tool) == str(tool)


# ---------- fields -----------------------------------------------------------


def test_block_is_callable_and_not_shown_in_str():
    tool = build_move_tool()

    assert tool.block("north") == "You move north into a torch-lit corridor."
    assert "lambda" not in str(tool)
    assert "function" not in str(tool)


def test_positional_construction_matches_ruby_struct_order():
    tool = Tool("move", "desc", {"direction": {}}, None)

    assert tool.name == "move"
    assert tool.description == "desc"
    assert tool.parameters == {"direction": {}}
    assert tool.block is None


def test_tools_compare_by_value():
    assert Tool("move", "desc", {}) == Tool("move", "desc", {})


def test_parameters_are_not_shared_between_instances():
    first, second = Tool("a"), Tool("b")
    first.parameters["direction"] = {}

    assert second.parameters == {}


# ---------- required_keys (new in step 10) -----------------------------------


def test_required_keys_defaults_to_every_parameter():
    """The behaviour every built-in relies on: no explicit list means all of them."""
    tool = Tool("t", "d", {"a": {}, "b": {}}, lambda: None)

    assert tool.required_keys() == ["a", "b"]


def test_an_explicit_required_list_wins():
    tool = Tool("t", "d", {"a": {}, "b": {}}, lambda: None, ["a"])

    assert tool.required_keys() == ["a"]


def test_an_empty_required_list_means_nothing_is_mandatory():
    """[] must not be confused with None — an MCP tool with all-optional params sends []."""
    tool = Tool("t", "d", {"a": {}}, lambda: None, [])

    assert tool.required_keys() == []


def test_required_keys_are_strings():
    tool = Tool("t", "d", {}, lambda: None, ["a"])

    assert all(isinstance(k, str) for k in tool.required_keys())
