"""Tests for `boukensha/mcp/client.py`.

Ruby step 10 ships no specs — see `docs/plans/python_port/10_standard_tool_library.md` §7.1.

Most tests drive a scripted server over in-memory pipes: no subprocess, no timing, no MUD. Only
the lifecycle tests spawn a real process, because reaping is the thing they assert.
"""

import json
import sys

import pytest
from boukensha.mcp.client import Client, McpError


class ScriptedServer:
    """Stands in for the child process: canned responses, and a record of what was sent."""

    def __init__(self, *responses):
        self.sent = []
        self._responses = list(responses)
        self.stdin = self
        self.stdout = self
        self.closed = False

    # -- stdin side
    def write(self, data):
        self.sent.append(data)

    def flush(self):
        pass

    # -- stdout side
    def readline(self):
        if not self._responses:
            return ""
        entry = self._responses.pop(0)
        return entry if isinstance(entry, str) else json.dumps(entry) + "\n"

    def close(self):
        self.closed = True

    # -- process side
    def poll(self):
        return None

    def wait(self, timeout=None):
        return 0

    def terminate(self):
        pass

    def kill(self):
        pass


def wire(client, server):
    """Attach a scripted server without spawning anything."""
    client._proc = server
    return client


def ok(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def client_for(*responses):
    c = Client(name="test", command="unused")
    return wire(c, ScriptedServer(*responses)), c._proc


def sent_messages(server):
    return [json.loads(line) for line in server.sent]


# ---------- handshake --------------------------------------------------------


def test_start_sends_initialize_then_the_initialized_notification():
    client, server = client_for(ok(1, {"serverInfo": {"name": "srv", "version": "9"}}))

    client.start()

    methods = [m["method"] for m in sent_messages(server)]
    assert methods == ["initialize", "notifications/initialized"]


def test_the_initialized_notification_has_no_id():
    """A notification with an id would make the server reply, desynchronising the stream."""
    client, server = client_for(ok(1, {"serverInfo": {}}))

    client.start()

    notification = sent_messages(server)[1]
    assert "id" not in notification


def test_start_records_server_info():
    client, _ = client_for(ok(1, {"serverInfo": {"name": "mud-manager", "version": "0.2.0"}}))

    client.start()

    assert client.server_info == {"name": "mud-manager", "version": "0.2.0"}


def test_start_is_idempotent():
    client, server = client_for(ok(1, {"serverInfo": {}}))
    client.start()
    client.start()

    assert [m["method"] for m in sent_messages(server)].count("initialize") == 1


# ---------- tools ------------------------------------------------------------


def test_tools_list():
    client, _ = client_for(
        ok(1, {"serverInfo": {}}),
        ok(2, {"tools": [{"name": "look"}, {"name": "move"}]}),
    )
    client.start()

    assert [t["name"] for t in client.tools()] == ["look", "move"]


def test_call_tool_returns_joined_text():
    client, _ = client_for(
        ok(1, {"serverInfo": {}}),
        ok(2, {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}),
    )
    client.start()

    assert client.call_tool("look") == "a\nb"


def test_call_tool_sends_name_and_arguments():
    client, server = client_for(ok(1, {"serverInfo": {}}), ok(2, {"content": []}))
    client.start()
    client.call_tool("move", {"direction": "north"})

    call = sent_messages(server)[-1]
    assert call["params"] == {"name": "move", "arguments": {"direction": "north"}}


def test_is_error_becomes_an_ERROR_string_not_an_exception():
    """A tool failure is a message for the model, not a transport fault."""
    client, _ = client_for(
        ok(1, {"serverInfo": {}}),
        ok(2, {"content": [{"type": "text", "text": "invalid direction"}], "isError": True}),
    )
    client.start()

    assert client.call_tool("move") == "ERROR: invalid direction"


def test_non_text_content_is_reported_not_silently_dropped():
    """The Ruby client drops it silently; naming it keeps a future non-text server honest."""
    client, _ = client_for(
        ok(1, {"serverInfo": {}}),
        ok(2, {"content": [
            {"type": "text", "text": "a room"},
            {"type": "image", "data": "BASE64", "mimeType": "image/png"},
        ]}),
    )
    client.start()

    result = client.call_tool("look")
    assert "a room" in result
    assert "1 non-text content block(s) omitted: image" in result


# ---------- protocol errors --------------------------------------------------


def test_a_jsonrpc_error_raises():
    client, _ = client_for(
        ok(1, {"serverInfo": {}}),
        {"jsonrpc": "2.0", "id": 2, "error": {"code": -32601, "message": "Method not found"}},
    )
    client.start()

    with pytest.raises(McpError, match="Method not found"):
        client.tools()


def test_an_interleaved_notification_does_not_desynchronise():
    """Servers may emit notifications between request and response."""
    client, _ = client_for(
        ok(1, {"serverInfo": {}}),
        {"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info"}},
        ok(2, {"tools": [{"name": "look"}]}),
    )
    client.start()

    assert [t["name"] for t in client.tools()] == ["look"]


def test_non_json_noise_on_stdout_is_ignored():
    client, _ = client_for(
        ok(1, {"serverInfo": {}}),
        "warning: something chatty\n",
        ok(2, {"tools": []}),
    )
    client.start()

    assert client.tools() == []


def test_a_closed_stdout_raises_rather_than_hanging():
    client, _ = client_for(ok(1, {"serverInfo": {}}))
    client.start()

    with pytest.raises(McpError, match="closed stdout"):
        client.tools()


def test_a_missing_command_raises_a_named_error():
    client = Client(name="ghost", command="definitely-not-a-real-binary-xyz")

    with pytest.raises(McpError, match="command not found"):
        client.start()


# ---------- lifecycle — these spawn a real process ---------------------------


def test_close_reaps_a_real_process():
    client = Client(name="cat", command=sys.executable, args=["-c", "import sys; sys.stdin.read()"])
    client._proc = __import__("subprocess").Popen(
        [sys.executable, "-c", "import sys; sys.stdin.read()"],
        stdin=__import__("subprocess").PIPE,
        stdout=__import__("subprocess").PIPE,
        text=True,
    )
    assert client.alive()

    client.close()

    assert not client.alive()


def test_close_is_safe_to_call_twice():
    client = Client(name="none", command="unused")
    client.close()
    client.close()
