# MUD over MCP — Implementation Reference

Companion to [`generic_interfacing.md`](generic_interfacing.md), which asked the
question and chose an answer. This one documents what was built.

**Status:** implemented and verified offline. 35/35 checks in
`week1_baseline/mcp/verify`. Not committed — the working tree holds it.

---

## 1. What problem this solves

Bootcampers want to write their agent harness in Java, Python, Rust or Go.
MudManager is Ruby. Naively that means every language reimplements a telnet
client, an IAC stripper and a CircleMUD login state machine.

It cannot be solved by shelling out per command, because **a MUD session is
stateful**: login state, in-world position, combat, and asynchronous chatter
that arrives *between* your commands. A fresh process per command would re-run
the 7-step login every time and the character would visibly disconnect and
reconnect in-game between every action.

So: one process owns the session; everything else is a front-end onto it.

---

## 2. Architecture

```
   Ruby harness        Python harness       Go / Rust / Java
        │                    │                     │
        └──────── MCP (JSON-RPC 2.0 over stdio) ───┘
                             │
                    mud-manager --mcp          ← shim; owns nothing
                             │
                    UNIX socket, JSON lines
                             │
                    mud-manager daemon         ← owns the sessions
                       │            │
                  Session      Session         ← one telnet socket each
                       │            │
                    CircleMUD    CircleMUD
```

Three layers, each with one job:

| Layer | Owns | Lifetime |
|---|---|---|
| `Daemon` | telnet sessions, reconnection | long — survives every client |
| `McpServer` | nothing; translation only | one agent run |
| `CLI` | nothing; translation only | one command |

**Why the MCP server owns nothing.** MCP's stdio transport makes the server a
child process of the host. A server that held the session would lose it whenever
the agent restarted — a fresh login and a visible reconnect in-game, exactly when
a student iterates fastest. This is option (b) from the exploration doc §3.

---

## 3. File map

### `week0_explore/mud_manager` — the server side

| File | Lines | Role |
|---|---|---|
| `lib/mud_manager/session.rb` | 271 | *(existing)* one telnet connection, IAC stripping, login |
| `lib/mud_manager/primitives.rb` | 418 | *(existing)* 58 typed CircleMUD command builders |
| `lib/mud_manager/tool_table.rb` | **356** | the agent-facing surface: 31 gameplay + 3 session tools |
| `lib/mud_manager/daemon.rb` | **248** | session ownership, multi-session, reconnect |
| `lib/mud_manager/cli.rb` | **197** | shell-out front-end |
| `lib/mud_manager/mcp_server.rb` | **194** | JSON-RPC 2.0 over stdio |
| `lib/mud_manager/daemon_client.rb` | **71** | socket client, auto-starts the daemon |
| `bin/mud-manager` | **9** | executable |

Two edits to existing code:

- `session.rb` — `open?` now returns a real boolean. `@socket && !@closed` yields
  `nil` once the socket is gone, and the daemon serialises that value into JSON.
- `mud_manager.gemspec` — declares `bin/mud-manager` as an executable and ships
  `README.md`.

### `week1_baseline/ruby/10_standard_tool_library` — the host side

| File | Lines | Role |
|---|---|---|
| `lib/boukensha/mcp/client.rb` | **156** | MCP stdio client: spawn, handshake, `tools/list`, `tools/call` |
| `lib/boukensha/tools/mcp.rb` | **100** | registers a server's tools into the Registry |

Edits to existing code:

| File | Change | Why |
|---|---|---|
| `lib/boukensha/tool.rb` | `Tool` gains `required`; `#required_keys` | see §6.1 |
| `lib/boukensha/registry.rb` | `tool(..., required:)`, `registered?` | pass the list; detect collisions |
| `lib/boukensha/backends/*.rb` (×5) | `required: tool.required_keys` | see §6.1 |
| `lib/boukensha/config.rb` | `mcp_servers` reader + `normalize_server` | read the config block |
| `lib/boukensha.rb` | start servers in `run`/`repl`, close in `ensure` | wiring |

### `week1_baseline/mcp` — verification artifacts

| File | Lines | Role |
|---|---|---|
| `verify` | 378 | 35 checks across all six layers, fully offline |
| `python_client_demo.py` | 173 | cross-language proof, stdlib only |
| `README.md` | 97 | how to run it |
| `fake_mud_server.rb` | 83 | stub CircleMUD: login dance, `> ` prompt, IAC bytes |
| `settings.example.yaml` | 48 | the `mcp_servers:` block to paste |

---

## 4. The tool surface

34 tools, all generated from `MudManager::ToolTable`.

**3 session tools**, handled by the daemon: `mud_connect`, `mud_disconnect`,
`mud_status`.

**31 gameplay tools**, dispatched into `Primitives`:

| Group | Tools |
|---|---|
| Movement | `move` `set_position` `flee` `enter` `follow` `track` |
| Looking | `look` `examine` `info_self` `info_world` `consider` `diagnose` `report_hp` |
| Combat | `attack` `skill_strike` `cast_spell` `use_magic_item` |
| Talking | `say` `tell` `channel_say` |
| Objects | `get_item` `drop_item` `put_item` `give_item` `equip_item` `consume_item` `door` |
| Other | `shop` `practice` `save_character` `send_raw` |

`send_raw` is the escape hatch for anything the curated set doesn't cover.

---

## 5. Protocol reference

Two wire formats. Only the first matters to a bootcamper.

### 5.1 MCP (agent ↔ `mud-manager --mcp`)

Standard MCP over stdio: newline-delimited JSON-RPC 2.0, no Content-Length
framing. Methods: `initialize`, `notifications/initialized`, `ping`,
`tools/list`, `tools/call`.

```jsonc
// ->
{"jsonrpc":"2.0","id":1,"method":"tools/call",
 "params":{"name":"move","arguments":{"direction":"north"}}}

// <-
{"jsonrpc":"2.0","id":1,"result":{
  "content":[{"type":"text","text":"You walk north.\n..."}],
  "isError":false}}
```

**Tool failures are results, not protocol errors.** A bad enum comes back with
`isError: true` and a readable message. A JSON-RPC `error` would imply the *call*
was malformed; "you can't wield a corpse" is a normal outcome the model should
read and react to. `-32601 Method not found` is reserved for genuine protocol
faults.

Credentials arrive as environment variables from the host's `mcp_servers:` block:
`MUD_HOST`, `MUD_PORT`, `MUD_USERNAME`, `MUD_PASSWORD`, `MUD_SESSION`.

### 5.2 Daemon socket (internal)

Newline-delimited JSON over a UNIX socket at `$MUD_MANAGER_SOCKET`, default
`~/.mud_manager/daemon.sock`, mode 0600. One request per line, one response per
line. Documented because any language can speak it directly if MCP is overkill.

| op | Request fields | Response |
|---|---|---|
| `ping` | — | `protocol`, `pid` |
| `open` | `session`, `host`, `port`, `username`, `password` | `already_open` |
| `send` | `session`, `tool`, `args` *or* `command` | `output`, `reconnected` |
| `raw` | `session`, `line` | `output`, `reconnected` |
| `sessions` | — | `sessions[]` |
| `close` | `session` | — |
| `shutdown` | — | — |

Every response carries `ok`; failures carry `error`.

---

## 6. Design decisions

### 6.1 Optional parameters (a bug found during integration)

All five backends built their schema as:

```ruby
required: tool.parameters.keys.map(&:to_s)   # every parameter, always
```

Fine for the built-ins, which only declare mandatory parameters. Wrong for MCP
tools, whose JSON Schema carries a real `required` list — `look` takes an
optional target. Without a fix, every optional parameter would be advertised to
the model as mandatory.

`Tool#required_keys` returns `required || parameters.keys`, so the default is the
old behaviour and no existing tool changes. Verified end to end: `look` arrives
with `required: []`, `move` with `["direction"]`, enums intact.

### 6.2 Reconnection: transparent, not silent

If the socket died, the daemon reconnects and re-logs-in, then sets
`reconnected: true`. The MCP server prefixes the output with
`[session reconnected]`.

A reconnect loses everything said while the socket was down. An agent that isn't
told will confidently misread the room. Hiding it would be the easy choice and
the wrong one.

### 6.3 One table, not three transcriptions

The command surface previously existed twice by hand — 58 `Primitives` methods
and 27 `Tools::Mud` registrations — and MCP would have made it three. Drift
between copies fails *silently*: a schema promising an enum the primitive
rejects breaks only at runtime, on that one argument, mid-session.

`ToolTable` now generates the MCP schema and the dispatch. Adding a command is
one edit. This is the argument that holds even if CircleMUD stays the only MUD.

### 6.4 Validation stays in Ruby

`Primitives` keeps doing enum and argument checking. A Python caller sending
`direction: "sideways"` gets
`invalid direction: "sideways" (expected one of north, east, …)` rather than a
mangled line reaching the MUD. Every language inherits the validation for free.

### 6.5 Name collisions raise

Two servers exposing `read_file` would otherwise silently shadow one another,
and the failure surfaces as *the wrong thing happening*, which is nearly
impossible to trace back. `Tools::Mcp` raises and names the `prefix:` fix.

### 6.6 Auto-start and auto-connect

`DaemonClient` spawns a detached daemon if none is listening, and the MCP server
opens a session on first gameplay call when credentials are configured. Both
exist so nobody has to remember a startup ritual. Auto-connect only fires when
`MUD_USERNAME` is set; otherwise the model is told to call `mud_connect`.

---

## 7. Using it

### From Boukensha (Ruby, step 10)

Paste the `mcp_servers:` block from `week1_baseline/mcp/settings.example.yaml`
into `.boukensha/settings.yaml`. Tools appear on the next run.

**One decision when enabling it.** Step 10 still ships `Tools::Mud`, which
registers `look`, `move`, `attack` under the bare names. Either pass
`mud: false` to `Boukensha.repl` / `.run`, or set `prefix: mud` so the MCP tools
become `mud_look` and friends. Without one of those, §6.5 raises.

### From another language

Write ~60 lines of MCP client — see `python_client_demo.py`, which is stdlib
only. That client is not MUD-specific: it is how the harness will get filesystem
and shell tools too.

### From a shell

```sh
mud-manager connect --user NAME --password PW
mud-manager tool look
mud-manager tool move direction=north
mud-manager sessions
mud-manager stop
```

Zero dependencies. Useful as a debugging path and as a fallback for a language
whose MCP story isn't ready.

---

## 8. Verification

```sh
./week1_baseline/mcp/verify                    # 35 checks, ~5s
./week1_baseline/mcp/python_client_demo.py     # cross-language proof
```

Both are **fully offline** — a stub CircleMUD stands in for the game and no API
call is made. That is deliberate: a check that costs money or needs a live game
is a check nobody runs.

Coverage by layer: Session (4) · ToolTable (6) · Daemon (8) · CLI (4) ·
McpServer (6) · Boukensha bridge (7).

The checks worth knowing about:

- **"a SECOND client sees the session the first opened"** — the entire premise.
- **"tools/call reports a bad enum as isError, not a JSON-RPC error"** — pins §5.1.
- **"optional params stay optional through the bridge"** — pins §6.1 end to end.
- **"a notification gets no reply"** — answering a notification desynchronises
  the JSON-RPC stream, and the failure would look like unrelated corruption.

---

## 9. Known gaps and future work

1. **`Tools::Mud` was not deleted.** `ITERATIONS.md` §10 wants every capability
   to arrive over MCP and the built-in tool modules gone. This change adds the
   MCP path *alongside*, so nothing that works today breaks. Removing them is a
   separate decision.
2. **The built-ins still over-declare required parameters.** `Tools::Mud`'s
   `look` reports `required_keys == ["target", "preposition"]` though both are
   optional. §6.1 makes this fixable; it isn't fixed.
3. **`.boukensha/settings.yaml` was not modified.** Enabling MCP changes what
   every run does, so the block lives in `settings.example.yaml` for you to
   paste. Note that file holds a plaintext MUD password and **is not gitignored**
   — only `.env` and `.boukensha/sessions/` are.
4. **No daemon eviction.** Sessions live until closed or the daemon stops. A
   long-running daemon with abandoned sessions holds telnet connections open.
5. **Single-machine only.** The daemon listens on a UNIX socket, so clients must
   share a filesystem. Fine for a bootcamper's laptop; a hosted setup would need
   the HTTP transport (exploration doc §3c).
6. **Still CircleMUD-only.** This solves the *language* axis. The *dialect* axis
   — login dance, `"> "` prompt sentinel, and the CircleMUD verb surface — is
   untouched. `ToolTable` is the seam a second dialect would plug into, but no
   second dialect exists, so genericity across MUDs remains an untested claim.
7. **No unit tests in the gem.** `verify` is an integration harness. The
   golden-transcript unit test proposed in the exploration doc §8 was not built.
