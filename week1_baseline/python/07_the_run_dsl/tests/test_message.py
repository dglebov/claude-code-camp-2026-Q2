from boukensha.message import Message


def test_str_without_tool_use_id():
    message = Message("user", "Explore north and tell me what you find.")

    assert str(message) == "#<Message role=user content=Explore north and tell me what you find....>"


def test_str_with_tool_use_id_adds_bracketed_tag():
    message = Message("tool_result", "You move north.", "toolu_01X")

    assert str(message) == "#<Message role=tool_result [toolu_01X] content=You move north....>"


def test_content_truncated_at_exactly_61_characters():
    """Ruby's [0..60] is an inclusive range. A naive [:60] silently drops a character."""
    message = Message("user", "a" * 100)

    assert "content=" + "a" * 61 + "..." in str(message)
    assert "a" * 62 not in str(message)


def test_short_content_is_not_padded():
    assert str(Message("user", "hi")) == "#<Message role=user content=hi...>"


def test_none_content_renders_empty_not_none():
    assert str(Message("user", None)) == "#<Message role=user content=...>"


def test_empty_tool_use_id_omits_the_tag():
    assert " [" not in str(Message("user", "hi", ""))


def test_repr_matches_str():
    message = Message("user", "hi")

    assert repr(message) == str(message)


def test_positional_construction_matches_ruby_struct_order():
    message = Message("assistant", "text", "toolu_1")

    assert message.role == "assistant"
    assert message.content == "text"
    assert message.tool_use_id == "toolu_1"


def test_tool_use_id_defaults_to_none():
    assert Message("user", "hi").tool_use_id is None


def test_messages_compare_by_value():
    assert Message("user", "hi") == Message("user", "hi")
    assert Message("user", "hi") != Message("assistant", "hi")
