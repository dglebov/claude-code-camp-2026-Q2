"""Port of `ruby/11_tui/lib/boukensha/mcp/client.rb`.

A minimal MCP client over the stdio transport: spawn a server, handshake, then `tools/list` and
`tools/call`. Server-agnostic — `command` / `args` / `env` is the standard stdio config, so this
talks to the MUD server, a filesystem server, or anything else that speaks MCP.

Messages are newline-delimited JSON-RPC 2.0, which is what the stdio transport specifies; there
is no Content-Length framing.

Two Python-specific hazards the Ruby version does not have (plan §5.2):

1. **`bufsize=1` only means line-buffered with `text=True`.** Without it the handshake can sit
   in a buffer while the host waits forever for a response the server already wrote.
2. **Never read the child's stderr synchronously while it is alive.** `proc.stderr.read()`
   blocks until the pipe closes — i.e. until the server exits — which it will not do, because
   it is waiting for the request the now-blocked host has not sent. Ruby's `read_nonblock` has
   no portable Python equivalent, so stderr is left **inherited** here: server diagnostics go
   straight to the terminal, and nothing in this process can deadlock on them.
"""

import json
import os
import subprocess
import time

from ..errors import ApiError

PROTOCOL_VERSION = "2024-11-05"
CLIENT_INFO = {"name": "boukensha", "version": "0.10.0"}
DEFAULT_TIMEOUT = 30.0


class McpError(ApiError):
    """An MCP transport or protocol failure. A *tool* failure is not this — see call_tool."""


class Client:
    def __init__(self, *, name, command, args=None, env=None, timeout=DEFAULT_TIMEOUT):
        self.name = str(name)
        self._command = command
        self._args = [str(a) for a in (args or [])]
        self._env = {str(k): str(v) for k, v in (env or {}).items()}
        self._timeout = timeout
        self._next_id = 0
        self._proc = None
        # Separate from `_proc` deliberately, mirroring Ruby's `@started`. Guarding on the
        # process alone would make an injected transport (as the tests use) look already
        # handshaken, silently skipping initialize.
        self._started = False
        self.server_info = {}

    # ---- lifecycle ---------------------------------------------------------

    def start(self):
        if self._started:
            return self

        if self._proc is None:
            self._spawn()

        self._started = True
        result = self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            },
        )
        self.server_info = result.get("serverInfo", {})

        # A notification: no id, and the server must not answer it. Answering one would
        # desynchronise the stream, so this is also asserted in the tests.
        self._notify("notifications/initialized")
        return self

    def _spawn(self):
        try:
            self._proc = subprocess.Popen(
                [self._command, *self._args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                # stderr deliberately inherited — see the module docstring.
                env={**os.environ, **self._env},
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as error:
            raise McpError(
                f"MCP server {self.name!r}: command not found: {self._command} ({error})"
            ) from error

    def close(self):
        if self._proc is None:
            return

        proc, self._proc = self._proc, None
        self._started = False
        try:
            if proc.stdin:
                proc.stdin.close()
        except OSError:
            pass

        # Give it a moment to exit on its own before insisting, mirroring Ruby's join(1).
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
        finally:
            if proc.stdout:
                proc.stdout.close()

    def alive(self):
        return self._proc is not None and self._proc.poll() is None

    # ---- API ---------------------------------------------------------------

    def tools(self):
        return self._request("tools/list").get("tools", [])

    def call_tool(self, name, arguments=None):
        """Return the tool's text content.

        MCP reports tool failures as a normal result with isError: true — that is a message for
        the model to read and react to, not a transport failure, so it comes back as text with an
        ERROR: prefix rather than raising.
        """
        result = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        text = "\n".join(
            block.get("text", "")
            for block in (result.get("content") or [])
            if block.get("type") == "text"
        )
        dropped = [b for b in (result.get("content") or []) if b.get("type") != "text"]
        if not text:
            text = json.dumps(result)
        elif dropped:
            # Named rather than silently discarded: the backends can carry image content, so a
            # future non-text server would otherwise lose data with no signal at all.
            kinds = ", ".join(sorted({b.get("type", "unknown") for b in dropped}))
            text = f"{text}\n[{len(dropped)} non-text content block(s) omitted: {kinds}]"

        return f"ERROR: {text}" if result.get("isError") else text

    # ---- JSON-RPC ----------------------------------------------------------

    def _request(self, method, params=None):
        if not self._started:
            self.start()

        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            message["params"] = params
        self._write(message)
        return self._read_until_id(self._next_id)

    def _notify(self, method, params=None):
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._write(message)

    def _write(self, message):
        try:
            self._proc.stdin.write(json.dumps(message) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as error:
            raise McpError(f"MCP server {self.name!r} exited: {error}") from error

    def _read_until_id(self, wanted):
        """Skip anything that is not the response we asked for.

        A server may legitimately interleave notifications; discarding them here keeps
        request/response correlation honest rather than assuming strict ordering.
        """
        deadline = time.monotonic() + self._timeout
        while True:
            if time.monotonic() > deadline:
                raise McpError(f"MCP server {self.name!r}: timed out after {self._timeout}s")

            line = self._proc.stdout.readline()
            if line == "":
                raise McpError(f"MCP server {self.name!r} closed stdout")

            line = line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue  # not JSON — server noise on stdout; ignore rather than die

            if message.get("id") != wanted:
                continue

            if "error" in message:
                err = message["error"]
                raise McpError(
                    f"MCP server {self.name!r}: {err.get('message')} (code {err.get('code')})"
                )

            return message.get("result") or {}
