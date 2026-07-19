#!/usr/bin/env python3
"""
Persistent telnet session manager for playing a MUD.

A MUD connection is a live, stateful stream -- the server pushes text
whenever it feels like it (room descriptions, combat rounds, other players'
chat), not just in response to a command. A one-shot "connect, send, read,
disconnect" script would lose everything that arrives between calls and
would force a fresh login for every single command. So this script instead
runs a small background daemon that holds the one real TCP connection open,
continuously drains it into a local log file, and exposes a tiny CLI
(start/send/read/status/stop) that a calling agent can invoke repeatedly
via ordinary one-shot Bash commands without needing an interactive shell.

Usage:
    mud_client.py start  [--host HOST] [--port PORT] [--session-dir DIR]
    mud_client.py send   TEXT [--wait SECONDS] [--session-dir DIR]
    mud_client.py read   [--tail N | --all] [--session-dir DIR]
    mud_client.py status [--session-dir DIR]
    mud_client.py stop   [--session-dir DIR]
"""
import argparse
import os
import re
import signal
import socket
import subprocess
import sys
import time

DEFAULT_SESSION_DIR = os.path.expanduser("~/.mud-player-session")

IAC, DONT, DO, WONT, WILL, SB, SE = 255, 254, 253, 252, 251, 250, 240
ANSI_RE = re.compile(rb"\x1b\[[0-9;]*[A-Za-z]")


def paths(session_dir):
    os.makedirs(session_dir, exist_ok=True)
    return {
        "pid": os.path.join(session_dir, "daemon.pid"),
        "control": os.path.join(session_dir, "control.sock"),
        "log": os.path.join(session_dir, "session.log"),
        "offset": os.path.join(session_dir, "read.offset"),
    }


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


class TelnetFilter:
    """Incrementally strips telnet IAC negotiation and ANSI color codes
    from a byte stream, replying WONT/DONT to any option the server
    proposes so the connection stays a plain, unauthenticated text feed."""

    IDLE, GOT_IAC, GOT_CMD, IN_SUB = range(4)

    def __init__(self, sock):
        self.sock = sock
        self.state = self.IDLE
        self.pending_cmd = None
        self.ansi_buf = b""

    def feed(self, data):
        out = bytearray()
        for b in data:
            if self.state == self.IDLE:
                if b == IAC:
                    self.state = self.GOT_IAC
                else:
                    out.append(b)
            elif self.state == self.GOT_IAC:
                if b in (WILL, WONT, DO, DONT):
                    self.pending_cmd = b
                    self.state = self.GOT_CMD
                elif b == SB:
                    self.state = self.IN_SUB
                elif b == IAC:
                    out.append(IAC)
                    self.state = self.IDLE
                else:
                    self.state = self.IDLE
            elif self.state == self.GOT_CMD:
                reply = DONT if self.pending_cmd == WILL else (
                    WONT if self.pending_cmd == DO else None)
                if reply is not None:
                    try:
                        self.sock.sendall(bytes([IAC, reply, b]))
                    except OSError:
                        pass
                self.state = self.IDLE
            elif self.state == self.IN_SUB:
                if b == SE:
                    self.state = self.IDLE
        return self._strip_ansi(bytes(out))

    def _strip_ansi(self, chunk):
        # ANSI escapes can straddle two reads; buffer a partial "\x1b..." tail
        # (an ESC, optionally followed by "[" and digits/semicolons, with no
        # terminating letter yet) so it gets completed and stripped next feed().
        buf = self.ansi_buf + chunk
        m = re.search(rb"\x1b(?:\[[0-9;]*)?$", buf)
        if m:
            self.ansi_buf = buf[m.start():]
            buf = buf[:m.start()]
        else:
            self.ansi_buf = b""
        return ANSI_RE.sub(b"", buf)


def cmd_start(args):
    p = paths(args.session_dir)
    if os.path.exists(p["pid"]):
        pid = int(open(p["pid"]).read().strip() or 0)
        if pid and pid_alive(pid):
            print(f"Already running (pid {pid}). Use 'status' or 'stop' first.")
            return 1
    open(p["log"], "wb").close()
    if os.path.exists(p["offset"]):
        os.remove(p["offset"])
    daemon_args = [sys.executable, os.path.abspath(__file__), "_daemon",
                   "--host", args.host, "--port", str(args.port),
                   "--session-dir", args.session_dir]
    subprocess.Popen(daemon_args, stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                      start_new_session=True)
    for _ in range(20):
        time.sleep(0.1)
        if os.path.exists(p["pid"]):
            break
    if not os.path.exists(p["pid"]):
        print("Daemon failed to start (no pidfile). Check the host/port are reachable.")
        return 1
    time.sleep(0.5)
    print(f"Connecting to {args.host}:{args.port} ... started. Call 'read' to see the banner.")
    return 0


def cmd_send(args):
    p = paths(args.session_dir)
    if not os.path.exists(p["control"]):
        print("Daemon not running. Run 'start' first.")
        return 1
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(p["control"])
            s.sendall(args.text.encode() + b"\n")
    except OSError as e:
        print(f"Could not reach daemon control socket: {e}")
        return 1
    if args.wait > 0:
        time.sleep(args.wait)
        print(_read_since(p), end="")
    return 0


def _read_since(p):
    offset = 0
    if os.path.exists(p["offset"]):
        offset = int(open(p["offset"]).read().strip() or 0)
    with open(p["log"], "rb") as f:
        f.seek(offset)
        data = f.read()
        new_offset = f.tell()
    with open(p["offset"], "w") as f:
        f.write(str(new_offset))
    return data.decode(errors="replace")


def cmd_read(args):
    p = paths(args.session_dir)
    if not os.path.exists(p["log"]):
        print("No session log yet. Run 'start' first.")
        return 1
    if args.all:
        print(open(p["log"], encoding="utf-8", errors="replace").read())
    elif args.tail is not None:
        with open(p["log"], "rb") as f:
            data = f.read()
        lines = data.decode(errors="replace").splitlines()
        print("\n".join(lines[-args.tail:]))
    else:
        text = _read_since(p)
        print(text, end="" if text.endswith("\n") else "\n")
    return 0


def cmd_status(args):
    p = paths(args.session_dir)
    if not os.path.exists(p["pid"]):
        print("Not running.")
        return 0
    pid = int(open(p["pid"]).read().strip() or 0)
    alive = pid_alive(pid)
    size = os.path.getsize(p["log"]) if os.path.exists(p["log"]) else 0
    print(f"pid={pid} alive={alive} log_bytes={size} session_dir={args.session_dir}")
    return 0


def cmd_stop(args):
    p = paths(args.session_dir)
    if not os.path.exists(p["pid"]):
        print("Not running.")
        return 0
    pid = int(open(p["pid"]).read().strip() or 0)
    if pid_alive(pid):
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            if not pid_alive(pid):
                break
            time.sleep(0.1)
    for key in ("pid", "control"):
        if os.path.exists(p[key]):
            os.remove(p[key])
    print("Stopped.")
    return 0


def _daemon_main(args):
    """Runs detached (via start_new_session=True). Owns the real MUD socket."""
    p = paths(args.session_dir)
    sock = socket.create_connection((args.host, args.port), timeout=10)
    sock.settimeout(None)

    with open(p["pid"], "w") as f:
        f.write(str(os.getpid()))

    if os.path.exists(p["control"]):
        os.remove(p["control"])
    ctrl = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    ctrl.bind(p["control"])
    ctrl.listen(8)
    ctrl.settimeout(0.5)

    stop_flag = {"stop": False}

    def handle_term(signum, frame):
        stop_flag["stop"] = True

    signal.signal(signal.SIGTERM, handle_term)

    log = open(p["log"], "ab", buffering=0)
    tfilter = TelnetFilter(sock)
    sock.settimeout(0.2)

    try:
        while not stop_flag["stop"]:
            try:
                data = sock.recv(4096)
                if data == b"":
                    log.write(b"\n[connection closed by server]\n")
                    break
                clean = tfilter.feed(data)
                if clean:
                    log.write(clean)
            except socket.timeout:
                pass
            except OSError:
                break

            try:
                conn, _ = ctrl.accept()
                with conn:
                    conn.settimeout(1)
                    buf = b""
                    try:
                        while not buf.endswith(b"\n"):
                            chunk = conn.recv(4096)
                            if not chunk:
                                break
                            buf += chunk
                    except socket.timeout:
                        pass
                    if buf:
                        line = buf.rstrip(b"\n")
                        log.write(b"> " + line + b"\n")
                        try:
                            sock.sendall(line + b"\r\n")
                        except OSError:
                            stop_flag["stop"] = True
            except socket.timeout:
                pass
    finally:
        try:
            sock.close()
        except OSError:
            pass
        try:
            ctrl.close()
        except OSError:
            pass
        for key in ("pid", "control"):
            if os.path.exists(p[key]):
                os.remove(p[key])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="connect and start the background session")
    s.add_argument("--host", default="localhost")
    s.add_argument("--port", type=int, default=4000)
    s.add_argument("--session-dir", default=DEFAULT_SESSION_DIR)
    s.set_defaults(func=cmd_start)

    s = sub.add_parser("send", help="send one line of input to the MUD")
    s.add_argument("text")
    s.add_argument("--wait", type=float, default=0.6,
                    help="seconds to wait then auto-print the new output (0 to skip)")
    s.add_argument("--session-dir", default=DEFAULT_SESSION_DIR)
    s.set_defaults(func=cmd_send)

    s = sub.add_parser("read", help="print output received since the last read")
    s.add_argument("--tail", type=int, default=None, help="show last N lines without consuming")
    s.add_argument("--all", action="store_true", help="show the entire log without consuming")
    s.add_argument("--session-dir", default=DEFAULT_SESSION_DIR)
    s.set_defaults(func=cmd_read)

    s = sub.add_parser("status", help="show whether the daemon is running")
    s.add_argument("--session-dir", default=DEFAULT_SESSION_DIR)
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("stop", help="close the connection and stop the daemon")
    s.add_argument("--session-dir", default=DEFAULT_SESSION_DIR)
    s.set_defaults(func=cmd_stop)

    s = sub.add_parser("_daemon", help=argparse.SUPPRESS)
    s.add_argument("--host", required=True)
    s.add_argument("--port", type=int, required=True)
    s.add_argument("--session-dir", required=True)
    s.set_defaults(func=_daemon_main)

    args = ap.parse_args()
    sys.exit(args.func(args) or 0)


if __name__ == "__main__":
    main()
