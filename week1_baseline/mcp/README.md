# MUD over MCP

Implementation of the plan in [`docs/plans/mud_manager/generic_interfacing.md`](../../docs/plans/mud_manager/generic_interfacing.md):
let bootcampers drive the MUD from Java, Python, Rust or Go without any of them
reimplementing a telnet client.

## The shape

```
   Ruby harness        Python harness       Go / Rust / Java
        │                    │                     │
        └──────── MCP (JSON-RPC 2.0 over stdio) ───┘
                             │
                    mud-manager --mcp          ← owns nothing; a shim
                             │
                    UNIX socket (JSON lines)
                             │
                    mud-manager daemon         ← owns the sessions
                             │
                      telnet ── CircleMUD
```

**The daemon is the whole design.** A MUD connection carries login state,
in-world state, and chatter that arrives between commands, so it has to outlive
any single client. The MCP server is deliberately a shim: MCP's stdio transport
makes the server a child of the agent process, and a server that owned the
session would lose it on every restart — a fresh 7-step login and a visible
disconnect/reconnect in-game, exactly when a student iterates fastest.

## Install first

`settings.example.yaml` uses `command: mud-manager`, so the gem has to be
installed and on `PATH`:

```bash
cd week0_explore/mud_manager
gem build mud_manager.gemspec
gem install ./mud_manager-0.2.0.gem
# if the binary is not on PATH:
ln -s "$(gem env | awk '/EXECUTABLE DIRECTORY/{print $4}')/mud-manager" ~/.local/bin/
```

Check it: `mud-manager tools` should list 34 tools.

**The host side matters too.** Steps 09 and earlier ship no `mcp/` directory, so
a globally installed `boukensha` from one of them cannot host an MCP server at
all. Either use step 10's launcher (which runs from source and always has it) or
install step 10:

```bash
cd week1_baseline/ruby/10_standard_tool_library
gem build boukensha.gemspec && gem install ./boukensha-0.10.0.gem
```

Bumping the gem version relocks dependent steps — run
`bundle update mud_manager` in `week1_baseline/ruby/10_standard_tool_library`,
or `bundle exec` there fails looking for the old version.

To skip installing entirely, point `command:` at the absolute path of
`week0_explore/mud_manager/bin/mud-manager`.

## Try it

Everything here is offline. No API key, no live MUD, no billed calls.

```bash
./week1_baseline/mcp/verify              # 35 checks across all six layers
./week1_baseline/mcp/python_client_demo.py   # Python drives the MUD
```

Note that `verify` runs the **repo source**, not the installed gem — deliberate,
since it tests what you just edited, but it means a stale install passes
unnoticed. After any `gem install`, check the binary separately with
`mud-manager tools`.

Against a real MUD:

```bash
MUD_HOST=localhost MUD_PORT=4000 MUD_USERNAME=you MUD_PASSWORD=pw \
  ./week1_baseline/mcp/python_client_demo.py --live
```

## Files

| File | What it is |
|---|---|
| `verify` | End-to-end check: Session → ToolTable → Daemon → CLI → MCP → Boukensha |
| `fake_mud_server.rb` | Stub CircleMUD — login dance, `> ` prompt, IAC bytes. Makes all of the above offline |
| `python_client_demo.py` | ~60 lines of stdlib Python driving the MUD. The cross-language proof |
| `settings.example.yaml` | The `mcp_servers:` block to paste into `.boukensha/settings.yaml` |

## Wiring it into Boukensha (step 10)

Copy the `mcp_servers:` block from `settings.example.yaml` into your
`.boukensha/settings.yaml`. Tools appear automatically on the next run.

**One thing to decide when you enable it.** Step 10 still ships the built-in
`Tools::Mud`, which registers its own `look`, `move`, `attack` and so on. If you
also load the MCP server unprefixed, the names collide — and `Tools::Mcp` raises
rather than letting one silently shadow the other, because a shadowed tool fails
as *the wrong thing happening in-game*, which is nearly untraceable. Either:

- pass `mud: false` to `Boukensha.repl` / `.run` to drop the built-ins, or
- set `prefix: mud` on the server so its tools become `mud_look`, `mud_move`, …

The eventual direction (`ITERATIONS.md` §10) is to delete the built-in tool
modules entirely and let every capability arrive over MCP. This change does not
do that — it adds the MCP path alongside, so nothing that works today breaks.

## What each language actually writes

| Language | For MUD access |
|---|---|
| Ruby | nothing — a config entry |
| Python | nothing — a config entry, once its harness speaks MCP |
| Go / Rust / Java | an MCP client (~60 lines, see the Python demo), which the harness needs anyway for filesystem and shell tools |
| any, fallback | `exec("mud-manager", "tool", "look")` — zero dependencies |

## Many players at once

Sessions run in parallel; commands within one session are serialised (a telnet
socket has no request ids, so interleaved sends would steal each other's output).
Five concurrent logins complete together, and one player logging in does not
delay anyone already playing.

Two things that bite silently:

- **Session names must differ.** They all default to `"default"`, so several
  students sharing a machine and socket land in the *same* session. Set
  `MUD_SESSION` per student or per character.
- **One daemon per machine by default.** Override with `MUD_MANAGER_SOCKET`.

## Design decisions worth knowing

- **Reconnection is transparent but not silent.** If the socket died, the daemon
  reconnects and re-logs-in, then sets `reconnected: true` so the result carries
  `[session reconnected]`. A reconnect loses everything said while the socket was
  down; an agent that isn't told will misread the room.
- **One table generates the tool surface.** `MudManager::ToolTable` produces both
  the MCP schema and the dispatch into `Primitives`. Before this the same
  information was transcribed by hand twice and would have been a third time —
  and drift between copies fails silently, on one argument, mid-session.
- **Validation stays in Ruby.** A Python caller sending `direction: "sideways"`
  gets `invalid direction: "sideways" (expected one of north, east, …)` rather
  than a mangled line reaching the MUD.
- **Tool failures are results, not protocol errors.** MCP reports them with
  `isError: true` inside a successful response. "You can't wield a corpse" is
  something the model should read and react to, not a transport fault.
