"""Tests for `boukensha/tools/file_system.py`.

Ruby step 10 ships no specs — see `docs/plans/python_port/10_standard_tool_library.md` §7.1.

The containment tests are the point of this file. Every path the agent supplies is attacker-
adjacent input as far as the sandbox is concerned, and the failure mode is silent: a tool that
reads outside the root just returns content, and nothing looks wrong.
"""

import os

import pytest
from boukensha.context import Context
from boukensha.registry import Registry
from boukensha.tools import file_system


@pytest.fixture
def root(tmp_path):
    (tmp_path / "a.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("gamma beta\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def reg(root):
    ctx = Context(system="t", working_dir=str(root))
    registry = Registry(ctx)
    file_system.register(registry, working_dir=str(root))
    return registry


@pytest.fixture
def ctx_of(reg):
    return reg._context


# ---------- registration -----------------------------------------------------


def test_registers_four_tools(ctx_of):
    """Step 12 disables list_directory and search_files — the player agent has no use for them,
    and Ruby's file_system.rb comments out the same two. Both trees must advertise the same
    surface to the model."""
    assert sorted(ctx_of.tools) == ["delete_file", "pwd", "read_file", "write_file"]


def test_the_disabled_tools_are_not_registered(ctx_of):
    assert "list_directory" not in ctx_of.tools
    assert "search_files" not in ctx_of.tools


def test_required_params_are_declared_required(ctx_of):
    assert ctx_of.tools["read_file"].required_keys() == ["path"]
    assert sorted(ctx_of.tools["write_file"].required_keys()) == ["content", "path"]


# ---------- pwd / list -------------------------------------------------------


def test_pwd_returns_the_root(reg, root):
    assert reg.dispatch("pwd", {}) == os.path.abspath(str(root))


def test_read_file(reg):
    assert reg.dispatch("read_file", {"path": "a.txt"}) == "alpha\nbeta\n"


def test_read_missing_file_is_an_error_string_not_an_exception(reg):
    assert reg.dispatch("read_file", {"path": "nope.txt"}).startswith("error:")


def test_write_file_creates_parent_directories(reg, root):
    result = reg.dispatch("write_file", {"path": "deep/nested/c.txt", "content": "hi"})

    assert result.startswith("ok: wrote 2 bytes")
    assert (root / "deep" / "nested" / "c.txt").read_text(encoding="utf-8") == "hi"


def test_write_file_reports_BYTES_not_characters(reg):
    """Ruby reports bytesize; a multibyte string would differ from len()."""
    result = reg.dispatch("write_file", {"path": "u.txt", "content": "é"})

    assert "2 bytes" in result


def test_delete_file(reg, root):
    assert reg.dispatch("delete_file", {"path": "a.txt"}).startswith("ok: deleted")
    assert not (root / "a.txt").exists()


def test_delete_directory_is_refused(reg, root):
    assert reg.dispatch("delete_file", {"path": "sub"}).startswith("error:")
    assert (root / "sub").is_dir()


# ---------- containment — the security surface ------------------------------


def test_absolute_paths_are_rejected(reg):
    assert reg.dispatch("read_file", {"path": "/etc/passwd"}).startswith("error:")


def test_parent_traversal_is_rejected(reg):
    assert reg.dispatch("read_file", {"path": "../../../etc/passwd"}).startswith("error:")


def test_traversal_that_returns_inside_is_allowed(reg):
    """sub/../a.txt normalises back inside the root and must not be rejected."""
    assert reg.dispatch("read_file", {"path": "sub/../a.txt"}) == "alpha\nbeta\n"


def test_a_sibling_directory_with_the_same_prefix_is_rejected(reg, root):
    """`/tmp/xyz` must not be treated as inside `/tmp/xy` — the check is on a path separator,
    not a bare string prefix."""
    outside = root.parent / (root.name + "-evil")
    outside.mkdir()
    (outside / "secret.txt").write_text("nope", encoding="utf-8")

    result = reg.dispatch("read_file", {"path": f"../{outside.name}/secret.txt"})

    assert result.startswith("error:")


def test_a_symlink_pointing_outside_the_root_is_FOLLOWED(reg, root, tmp_path_factory):
    """Deliberate, and a documented divergence risk (plan §5.4).

    Ruby's File.expand_path normalises without resolving symlinks, so the Ruby tree follows this
    link. os.path.abspath matches that; os.path.realpath or Path.resolve would NOT, and would
    make the two trees disagree on the same input. The stricter behaviour is arguably safer —
    this test exists so that choosing it later is a deliberate change rather than an accident.
    """
    outside = tmp_path_factory.mktemp("outside")
    (outside / "secret.txt").write_text("leaked", encoding="utf-8")
    os.symlink(outside, root / "link")

    assert reg.dispatch("read_file", {"path": "link/secret.txt"}) == "leaked"


# ---------- search -----------------------------------------------------------


