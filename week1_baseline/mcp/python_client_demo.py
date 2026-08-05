#!/usr/bin/env python3
"""Cross-language proof: Python driving the MUD with zero MUD code.

The whole premise of the exploration doc is that a bootcamper in Python, Go,
Rust or Java should not have to reimplement a telnet client, an IAC stripper
and a login state machine. This file is the evidence.

There is no `mud_manager` import here and no socket handling. Everything below
is stdlib: spawn the Ruby MCP server, speak newline-delimited JSON-RPC 2.0 to
it, call tools. The ~60 lines of MCP client here are the *entire* cost of MUD
support in a new language — and a harness needs that client anyway for
filesystem and shell tools.

Run against the fake MUD (no live game, no API key):

    ./week1_baseline/mcp/python_client_demo.py

Run against a real MUD:

    MUD_HOST=localhost MUD_PORT=4000 MUD_USERNAME=you MUD_PASSWORD=pw \\
      ./week1_baseline/mcp/python_client_demo.py --live
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MUD_LIB = ROOT / "week0_explore" / "mud_manager" / "lib"
MUD_BIN = ROOT / "week0_explore" / "mud_manager" / "bin" / "mud-manager"
FAKE_MUD = Path(__file__).resolve().parent / "fake_mud_server.rb"


class McpClient:
    """A complete MCP stdio client. This is all of it."""

    def __init__(self, command, args, env):
        self.proc = subprocess.Popen(
            [command, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env={**os.environ, **env},
            text=True,
            bufsize=1,
        )
        self._id = 0

    def _request(self, method, params=None):
        self._id += 1
        message = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            message["params"] = params
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server closed stdout")
            reply = json.loads(line)
            if reply.get("id") == self._id:
                if "error" in reply:
                    raise RuntimeError(reply["error"]["message"])
                return reply.get("result", {})

    def _notify(self, method):
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.proc.stdin.flush()

    def initialize(self):
        result = self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "python-demo", "version": "1.0"},
            },
        )
        self._notify("notifications/initialized")
        return result

    def list_tools(self):
        return self._request("tools/list")["tools"]

    def call_tool(self, name, arguments=None):
        result = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        text = "\n".join(
            block["text"] for block in result.get("content", []) if block.get("type") == "text"
        )
        return text, result.get("isError", False)

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        self.proc.terminate()


def main():
    live = "--live" in sys.argv
    children = []

    if live:
        env = {
            "MUD_HOST": os.environ.get("MUD_HOST", "localhost"),
            "MUD_PORT": os.environ.get("MUD_PORT", "4000"),
            "MUD_USERNAME": os.environ["MUD_USERNAME"],
            "MUD_PASSWORD": os.environ["MUD_PASSWORD"],
            "MUD_SESSION": "python-demo",
        }
        print(f"Connecting to real MUD at {env['MUD_HOST']}:{env['MUD_PORT']}")
    else:
        fake = subprocess.Popen(
            ["ruby", str(FAKE_MUD), "0"], stdout=subprocess.PIPE, text=True
        )
        children.append(fake)
        port = fake.stdout.readline().strip()
        socket_dir = tempfile.mkdtemp(prefix="mud-manager-py")
        env = {
            "MUD_HOST": "127.0.0.1",
            "MUD_PORT": port,
            "MUD_USERNAME": "PyTester",
            "MUD_PASSWORD": "secret",
            "MUD_SESSION": "python-demo",
            "MUD_MANAGER_SOCKET": str(Path(socket_dir) / "daemon.sock"),
        }
        print(f"Fake MUD on 127.0.0.1:{port}")

    client = McpClient("ruby", [f"-I{MUD_LIB}", str(MUD_BIN), "--mcp"], env)

    try:
        info = client.initialize()
        server = info.get("serverInfo", {})
        print(f"Connected to MCP server: {server.get('name')} {server.get('version')}")

        tools = client.list_tools()
        print(f"Discovered {len(tools)} tools, e.g. {', '.join(t['name'] for t in tools[:6])}...")

        print("\n--- look ---")
        text, is_error = client.call_tool("look")
        print(text.strip()[:400] or "(no output)")

        print("\n--- info_self kind=score ---")
        text, is_error = client.call_tool("info_self", {"kind": "score"})
        print(text.strip()[:300] or "(no output)")

        print("\n--- move direction=north ---")
        text, is_error = client.call_tool("move", {"direction": "north"})
        print(text.strip()[:300] or "(no output)")

        # Validation still happens Ruby-side, in Primitives. Python sent a bad
        # value and got a readable explanation rather than a mangled MUD line.
        print("\n--- move direction=sideways (should fail cleanly) ---")
        text, is_error = client.call_tool("move", {"direction": "sideways"})
        print(f"isError={is_error}: {text.strip()[:200]}")

        print("\n--- mud_status ---")
        text, _ = client.call_tool("mud_status")
        print(text.strip())

        print("\nPython drove a MUD session without one line of MUD code.")
    finally:
        client.close()
        for child in children:
            child.terminate()


if __name__ == "__main__":
    main()
