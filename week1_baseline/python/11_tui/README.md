# 11 · A Terminal UI (Python)

Python port of `week1_baseline/ruby/11_tui`.

Step 10 gave the agent a tool library. Step 11 gives the *session* a face: a four-zone
full-screen display, and — more importantly — the two seams on `Repl` that made it possible
without forking the REPL.

```
┌──────────────────────────────────────────────┐
│  conversation log (scrollable)               │
├──────────────────────────────────────────────┤
│  ⟳ live progress line (idle text when calm)  │
├──────────────────────────────────────────────┤
│  boukensha> input box                        │
├──────────────────────────────────────────────┤
│  status line (always on)                     │
└──────────────────────────────────────────────┘
```

## The substitution: Textual for Charm

Ruby's TUI is built on `bubbletea` + `lipgloss` + `bubbles` — Ruby bindings over Go's Charm
libraries. Nothing binds those from Python, so this is the one place in the tree where the port
swaps the underlying library rather than translating it. **Textual** is the choice: it is the
only option whose model (widgets, a message pump, reactive redraw, worker threads, alt-screen)
maps onto Bubbletea closely enough that `tui.py` and `tui.rb` still read as the same program.

| Bubbletea (Ruby) | Textual (Python) |
|---|---|
| `Bubbletea::Runner#run` | `App.run()` |
| `init` → `Bubbletea.tick(0.06)` | `set_interval(0.06, self._tick)` |
| `update(msg)` case on message class | `on_key` / bindings / the interval callback |
| `view` → join four rendered strings | `compose()` yields four widgets, updated in place |
| `Bubbles::Viewport` | `RichLog` |
| `Bubbles::TextArea` | `Input` |
| `Lipgloss::Style` | Textual CSS |
| `@dirty` + `sync_viewport` | *(nothing — Textual redraws on mutation)* |

Textual is the second runtime dependency in this tree, after PyYAML, and it is confined to this
step. Steps 00–10 do not import it.

## What's new

### `Repl` — two seams, and public accessors

| Added | Why |
|---|---|
| `on_output(callback)` | Redirects everything the REPL would print. When set, stdout is untouched. |
| `handle_command(entry)` | Command dispatch lifted out of the read loop. Returns `"quit"`, `"command"`, or `None`. |
| `banner()`, `run_turn()` | Were `_banner` / `_run_turn`; the TUI calls both. |
| `logger`, `context`, `model`, `version` properties | Ruby's `attr_reader`. A front-end needs them for the status line and to subscribe to log events. |

With no callback registered, behaviour is unchanged — which is what keeps `--no-tui` byte-for-byte
identical to Ruby's plain REPL.

### `Logger.subscribe` finally has a subscriber

Ported faithfully in step 07 and unused ever since. The TUI subscribes to drive the live progress
line — iteration number, current tool, token counts. `Context.tool_count` is the same story: it
has existed all along, and the status bar is its first reader.

### `boukensha.repl(tui=True)`

Default. `tui=False` — or `--no-tui` on the launcher — runs the plain terminal REPL.

## Differences from the Ruby original

### ESC cancels at an iteration boundary, not mid-request

**The one behavioural difference worth knowing.** Ruby aborts a running turn with
`@turn_thread.raise(Interrupt)`. Python has no safe equivalent: `PyThreadState_SetAsyncExc` is
documented as unsafe, and it cannot interrupt a thread parked in a blocking socket read — which
is exactly where an agent turn spends most of its time.

So cancellation here is **cooperative**. ESC sets a `threading.Event`; `Agent` checks it once per
iteration, before the next API call, and raises `Interrupted`. The practical consequence:

> Pressing ESC during a slow API call waits for that call to return. Ruby aborts it immediately.

The event is passed to the `Agent` constructor rather than to `run()`, so `run()` keeps the
signature it had in step 10.

### Non-TTY runs fall back to the plain REPL automatically

`repl()` checks `sys.stdin.isatty() and sys.stdout.isatty()` and drops to the terminal REPL when
either is false. A full-screen app cannot work under pytest, a pipe, or CI. Ruby relies on the
`--no-tui` flag alone; this guard is Python-side only.

### The bubbletea patch is not ported

`ruby/11_tui/patches/bubbletea/` fixes a bug in the gem's C extension: `program_poll_event` read
up to 256 bytes, parsed one key event, and discarded the rest, so pastes and fast typing lost
everything after the first character. Textual has no such defect, so there is nothing to port —
but `test_tui.py` carries a 43-character burst test precisely because the fix is *not* inherited.

### MUD tools still arrive over MCP

Unchanged from step 10, and worth restating because Ruby's step 11 shipped upstream with the old
built-in `Tools::Mud` restored: both trees now serve all MUD gameplay from `mud-manager --mcp`,
declared under `mcp_servers:` in `settings.yaml`. 41 tools, same names on both sides.

## Run

```sh
week1_baseline/bin/python/11_tui              # Textual TUI
week1_baseline/bin/python/11_tui --no-tui     # plain terminal REPL
week1_baseline/bin/python/11_tui --demo       # one-shot example, no session
```

Keys: `Enter` submit · `ESC` interrupt the turn · `Ctrl+L` clear history · `PgUp`/`PgDn` scroll ·
`Ctrl+C` / `Ctrl+D` quit. Slash commands (`/help`, `/clear`, `/quiet`, `/loud`, `/exit`) work in
both front-ends.

## Test

```sh
cd week1_baseline/python && ./run-tests          # every iteration, isolated
uv run pytest 11_tui/tests -q                    # this step only
```

537 tests: step 10's 497 plus 40 for the new seams and the TUI state machine. Almost all of them
run without booting Textual — `_write` is stubbed and events are fed to the handler directly. One
test does boot the real app through Textual's headless pilot, and it earns its keep: it caught a
name collision (`self._context` shadowing Textual's own `App._context`) that made the TUI
unusable and that no stubbed test could have found.

MCP end-to-end, offline and free:

```sh
week1_baseline/mcp/verify-python                 # defaults to this step
week1_baseline/mcp/verify-python 10_standard_tool_library
```
