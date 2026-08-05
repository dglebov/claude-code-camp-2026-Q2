"""Tests for `boukensha/tools/shell.py`.

Ruby step 10 ships no specs — see `docs/plans/python_port/10_standard_tool_library.md` §7.1.

Note what is deliberately NOT asserted: that `allowed_commands` is a security boundary. It is
not, in either tree — see `test_the_allow_list_is_bypassable_by_design`.
"""

import pytest
from boukensha.context import Context
from boukensha.registry import Registry
from boukensha.tasks import Player
from boukensha.tools import shell


def build(root, **kwargs):
    ctx = Context(task=Player, system="t", working_dir=str(root))
    registry = Registry(ctx)
    shell.register(registry, working_dir=str(root), **kwargs)
    return registry


@pytest.fixture
def reg(tmp_path):
    (tmp_path / "marker.txt").write_text("here\n", encoding="utf-8")
    return build(tmp_path)


# ---------- registration -----------------------------------------------------


def test_registers_one_tool(reg):
    assert list(reg._context.tools) == ["run_command"]


def test_the_allow_list_appears_in_the_description(tmp_path):
    reg = build(tmp_path, allowed_commands=["git", "python3"])

    assert "git, python3" in reg._context.tools["run_command"].description


# ---------- execution --------------------------------------------------------


def test_runs_a_command_and_returns_output(reg):
    assert reg.dispatch("run_command", {"command": "echo hello"}).strip() == "hello"


def test_runs_inside_the_working_directory(reg, tmp_path):
    out = reg.dispatch("run_command", {"command": "ls"})

    assert "marker.txt" in out


def test_combines_stdout_and_stderr(reg):
    out = reg.dispatch("run_command", {"command": "echo out; echo err 1>&2"})

    assert "out" in out
    assert "err" in out


def test_a_failing_command_reports_its_exit_code(reg):
    out = reg.dispatch("run_command", {"command": "exit 3"})

    assert "[exit 3]" in out


def test_a_silent_command_says_so(reg):
    assert reg.dispatch("run_command", {"command": "true"}) == "(no output)"


def test_a_timeout_is_an_error_string_not_an_exception(tmp_path):
    reg = build(tmp_path, timeout=1)

    out = reg.dispatch("run_command", {"command": "sleep 5"})

    assert out.startswith("error:")
    assert "timed out after 1s" in out


# ---------- allow-list -------------------------------------------------------


def test_allow_list_permits_a_listed_executable(tmp_path):
    reg = build(tmp_path, allowed_commands=["echo"])

    assert reg.dispatch("run_command", {"command": "echo ok"}).strip() == "ok"


def test_allow_list_rejects_an_unlisted_executable(tmp_path):
    reg = build(tmp_path, allowed_commands=["echo"])

    out = reg.dispatch("run_command", {"command": "ls"})

    assert out.startswith("error:")
    assert "not in the allowed-commands list" in out


def test_no_allow_list_permits_anything(reg):
    assert "marker.txt" in reg.dispatch("run_command", {"command": "ls"})


def test_the_allow_list_is_bypassable_by_design(tmp_path):
    """Pins a KNOWN weakness rather than pretending it isn't there.

    Ruby's Open3.capture2e is given a string, and Ruby hands a string with shell metacharacters
    to the shell — verified against the reference. The port mirrors that with shell=True. The
    consequence is that the allow-list only inspects the FIRST token, so a chained command runs
    regardless. Both trees behave this way.

    If this test ever fails, someone has tightened the sandbox — which is a fine thing to do
    deliberately, and should be mirrored in Ruby and documented, not silently diverged.
    """
    reg = build(tmp_path, allowed_commands=["echo"])

    out = reg.dispatch("run_command", {"command": "echo first; echo second"})

    assert "first" in out
    assert "second" in out


def test_shell_features_work(reg):
    """Pipelines and redirection have to keep working — Ruby's tree accepts them."""
    assert reg.dispatch("run_command", {"command": "echo hi | tr a-z A-Z"}).strip() == "HI"
