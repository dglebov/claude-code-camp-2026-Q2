"""Tests for `boukensha/tools/mcp.py` — the Registry bridge.

Ruby step 10 ships no specs — see `docs/plans/python_port/10_standard_tool_library.md` §7.1.

A fake Client stands in for the transport, so none of this spawns a process. The transport
itself is covered by `test_mcp_client.py`.
"""

from typing import ClassVar

import pytest
from boukensha.context import Context
from boukensha.registry import Registry
from boukensha.tasks import Player
from boukensha.tools import mcp

LOOK = {
    "name": "look",
    "description": "Look at the room.",
    "inputSchema": {
        "type": "object",
        "properties": {"target": {"type": "string", "description": "What to look at"}},
    },
}
MOVE = {
    "name": "move",
    "description": "Move one room.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "direction": {"type": "string", "description": "Way to go", "enum": ["north", "south"]}
        },
        "required": ["direction"],
    },
}


class FakeClient:
    """Records calls; never touches a process."""

    instances: ClassVar[list] = []

    def __init__(self, *, name, command, args=None, env=None, timeout=None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env
        self.calls = []
        self.closed = False
        self.started = False
        self._tools = [LOOK, MOVE]
        FakeClient.instances.append(self)

    def start(self):
        self.started = True
        return self

    def tools(self):
        return self._tools

    def call_tool(self, name, arguments=None):
        self.calls.append((name, arguments))
        return f"result of {name} {arguments}"

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def fake_client(monkeypatch):
    FakeClient.instances = []
    monkeypatch.setattr(mcp, "Client", FakeClient)
    return FakeClient


@pytest.fixture
def reg():
    ctx = Context(task=Player, system="t", working_dir=False)
    return Registry(ctx)


# ---------- registration -----------------------------------------------------


def test_registers_every_advertised_tool(reg):
    mcp.register(reg, name="mud", command="mud-manager", args=["--mcp"])

    assert sorted(reg._context.tools) == ["look", "move"]


def test_prefix_namespaces_names(reg):
    mcp.register(reg, name="mud", command="mud-manager", prefix="mud")

    assert sorted(reg._context.tools) == ["mud_look", "mud_move"]


def test_schema_survives_the_bridge(reg):
    mcp.register(reg, name="mud", command="mud-manager")

    move = reg._context.tools["move"]
    assert move.parameters["direction"]["enum"] == ["north", "south"]
    assert move.description == "Move one room."


def test_required_and_optional_are_preserved(reg):
    """The whole reason Tool gained `required`: `look`'s target is optional."""
    mcp.register(reg, name="mud", command="mud-manager")

    assert reg._context.tools["look"].required_keys() == []
    assert reg._context.tools["move"].required_keys() == ["direction"]


def test_dispatch_reaches_the_client_with_the_REMOTE_name(reg):
    """A prefix is a local rename only — the server is still called by its own name."""
    mcp.register(reg, name="mud", command="mud-manager", prefix="mud")

    reg.dispatch("mud_move", {"direction": "north"})

    assert FakeClient.instances[0].calls == [("move", {"direction": "north"})]


# ---------- collisions -------------------------------------------------------


def test_a_collision_raises_rather_than_shadowing(reg):
    mcp.register(reg, name="a", command="server-a")

    with pytest.raises(ValueError, match="collision"):
        mcp.register(reg, name="b", command="server-b")


def test_the_collision_message_names_the_fix(reg):
    mcp.register(reg, name="a", command="server-a")

    with pytest.raises(ValueError, match="prefix"):
        mcp.register(reg, name="b", command="server-b")


def test_prefixes_let_two_servers_coexist(reg):
    mcp.register(reg, name="a", command="server-a", prefix="a")
    mcp.register(reg, name="b", command="server-b", prefix="b")

    assert sorted(reg._context.tools) == ["a_look", "a_move", "b_look", "b_move"]


# ---------- failure handling -------------------------------------------------


def test_a_failed_start_raises_when_required(reg, monkeypatch):
    def boom(self):
        raise RuntimeError("no such server")

    monkeypatch.setattr(FakeClient, "start", boom)

    with pytest.raises(RuntimeError):
        mcp.register(reg, name="mud", command="mud-manager")


def test_required_false_downgrades_to_a_warning(reg, monkeypatch, capsys):
    def boom(self):
        raise RuntimeError("no such server")

    monkeypatch.setattr(FakeClient, "start", boom)

    result = mcp.register(reg, name="mud", command="mud-manager", required=False)

    assert result is None
    assert "unavailable, continuing without it" in capsys.readouterr().err
    assert reg._context.tools == {}


# ---------- register_all -----------------------------------------------------


def test_register_all_starts_each_configured_server(reg):
    clients = mcp.register_all(reg, [
        {"name": "a", "command": "server-a", "prefix": "a"},
        {"name": "b", "command": "server-b", "prefix": "b"},
    ])

    assert len(clients) == 2
    assert sorted(reg._context.tools) == ["a_look", "a_move", "b_look", "b_move"]


def test_register_all_skips_entries_with_no_command(reg):
    assert mcp.register_all(reg, [{"name": "broken"}]) == []


def test_register_all_tolerates_no_servers(reg):
    assert mcp.register_all(reg, None) == []
    assert mcp.register_all(reg, []) == []


def test_register_all_passes_env_and_args_through(reg):
    mcp.register_all(reg, [
        {"name": "mud", "command": "mud-manager", "args": ["--mcp"], "env": {"MUD_HOST": "h"}},
    ])

    client = FakeClient.instances[0]
    assert client.args == ["--mcp"]
    assert client.env == {"MUD_HOST": "h"}
