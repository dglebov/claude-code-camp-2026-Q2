# Step 11 — A Terminal UI: Ruby fixes + Python port

Reference: `week1_baseline/ruby/11_tui/`
Target:    `week1_baseline/python/11_tui/`

This plan has **two halves**. Half A repairs the Ruby step, which does not currently run at all.
Half B ports it to Python. Half A is not optional prep — the Ruby step is the reference the port
is checked against, so it has to be correct and runnable first.

> **Status: awaiting review.** Four questions in §1 change what gets built. Answer them inline in
> this file (as with `generic_interfacing.md`), then say execute.

---

## 1. Decisions

### Settled — do not re-litigate

| # | Decision | Why |
|---|---|---|
| D1 | The port targets `week1_baseline/python/11_tui/`, a full copy of the step-10 package plus the new files | Every step ships a self-contained `boukensha` package; this is the established shape |
| D2 | `Repl` gains the same seam Ruby added — `on_output`, `handle_command`, public `logger`/`context`/`model`/`version` | This refactor *is* the step's teaching content; the TUI is what it enables |
| D3 | The TUI wraps the REPL; it does not reimplement session logic | Ruby's design. Turn counting, `/commands`, and Agent dispatch stay in `Repl` |
| D4 | The bubbletea C patch has no Python counterpart | It fixes a bug in a Ruby gem's C extension (§5.6). The *class* of bug it guards is still worth a test |
| D5 | `--no-tui` is supported, and is the default in non-TTY contexts | Matches Ruby's flag; also required so `verify-python` and pytest never launch a full-screen app |

### Open — these block execution

#### Q1. Which TUI library? *(recommend: Textual)*

Ruby uses `bubbletea` + `lipgloss` + `bubbles` — Ruby bindings over Go's Charm libraries. There is
no Python binding to those, so this is a genuine substitution, not a translation.

| Option | Deps added | Maps to Bubbletea? | Verdict |
|---|---|---|---|
| **Textual** 8.2.8 | 10 packages | Very closely — widgets, message pump, reactive redraw, worker threads, alt-screen | **Recommended** |
| prompt_toolkit 3.0.53 | 2 packages | Partly — full-screen layout, but a different mental model | Viable if dep weight is the deciding factor |
| `curses` (stdlib) | 0 | Not at all | Rejected: ~600 lines of hand-rolled scrollback/wrapping/textarea, and the port stops resembling the Ruby |

Both were verified to install and import on this repo's Python 3.14.6. The tension is real:
`pyproject.toml` says the dep list is *"kept deliberately small… PyYAML is the one unavoidable
runtime dependency."* Textual breaks that. My argument for paying it: the whole value of this repo
is that the two trees read the same, and Textual is the only option where `update`/`view` map onto
something recognisable. A `curses` port would be correct and unreadable.

**If dep count is the priority, say so and I will use prompt_toolkit.**

#### Q2. Does step 11 keep MCP, or revert to the built-in `Tools::Mud`?

Upstream's step 11 branched from *upstream's* step 10, so it has **no MCP** and carries the old
480-line `lib/boukensha/tools/mud.rb` instead. Our step 10 deleted that file and moved all 34 MUD
tools to the `mud-manager --mcp` server.

Taking step 11 as-shipped would undo that: back to 27 duplicated built-in tools, no
`mcp_servers:` support, and a second login racing the MCP session (the exact double-login that
produced the `read_until` warning we fixed).

**Recommendation: re-apply the step-09/10 work onto step 11** (§8 lists the six items). Both trees
then keep the 41-tool, MCP-served shape that is already working and configured.

**Alternative:** keep step 11 faithful to upstream, and accept that it is a step backwards from
step 10. Cheaper, but `boukensha` installed globally would lose MUD-over-MCP.

#### Q3. Restore `/quiet` and `/loud`?

Upstream's step 11 deletes both commands, `Boukensha.quiet!/loud!/quiet?`, and their `HELP` lines.
Our step 10 has them. Plausibly deliberate (a TUI routes logging to the viewport, so muting it is
moot) — but it is silent removal, and Python step 10 has them too.

**Recommendation: keep them.** They cost nothing, the plain `--no-tui` REPL still benefits, and
dropping them creates a gratuitous Ruby/Python difference to explain.

#### Q4. Does Python need a loader equivalent?

Ruby has `boukensha_loader.rb` + a `bin/boukensha` gem executable, because step 09 made it a
globally installed command. Python has no such step — `bin/python/NN_*` shell launchers stand in.

**Recommendation: no loader.** Add `--no-tui` handling to the `bin/python/11_tui` launcher and
stop there. Building a Python global-executable story is step 09's job, and step 09 was never
ported.

---

## 2. Reference files — what to port

### New in this step

| Ruby | Lines | Python target |
|---|---|---|
| `lib/boukensha/tui.rb` | 324 | `boukensha/tui.py` |
| `patches/bubbletea/*` | — | **Not ported** — see D4 / §5.6 |

### Changed vs step 10

| Ruby | Change |
|---|---|
| `lib/boukensha/repl.rb` | `attr_reader :logger, :context, :model, :version`; `on_output`; `handle_command` extracted; `run_turn` routes through `output()`; `start` rebuilt on `handle_command` |
| `lib/boukensha.rb` | `repl(tui: true)`; constructs `Repl` then hands it to `Tui` |
| `lib/boukensha_loader.rb` | `--no-tui` flag |
| `lib/boukensha/version.rb` | `0.10.0` → `0.11.0` |

### Carried forward unchanged

Everything else: `agent.py`, `client.py`, `backends/`, `logger.py`, `prompt_builder.py`,
`registry.py`, `context.py`, `tool.py`, `tasks/`, `tools/`, `mcp/`, `run_dsl.py`, `message.py`,
`errors.py`, `env_file.py`, `config.py`.

---

## 3. What step 11 actually adds

Two things, and the second is the one that matters pedagogically:

**1. A four-zone full-screen display.**

```
┌────────────────────────────────────┐
│ conversation viewport (scrollable) │
├────────────────────────────────────┤
│ ⟳ live progress (hidden when idle) │
├────────────────────────────────────┤
│ boukensha> input box               │
├────────────────────────────────────┤
│ status line (always on)            │
└────────────────────────────────────┘
```

**2. The seam that made it possible.** Step 10's `Repl` printed directly and buried its command
handling inside the read loop, so nothing else could drive it. Step 11 splits output from
formatting (`on_output`) and command dispatch from the loop (`handle_command`). The TUI is then a
*consumer* of `Repl`, not a fork of it — and `Logger#subscribe`, added in step 07 and unused ever
since, finally has its first subscriber.

Both `Logger.subscribe` and `Context.tool_count` already exist in the Python tree, ported
faithfully when nothing called them. Step 11 is where that pays off — no new plumbing needed.

---

## 4. Target layout

```
week1_baseline/python/11_tui/
├── README.md
├── conftest.py
├── boukensha/
│   ├── __init__.py          # repl(tui=True); builds Repl, hands to Tui
│   ├── repl.py              # + on_output, handle_command, public accessors
│   ├── tui.py               # NEW
│   ├── version.py           # 0.11.0
│   └── … (rest copied from step 10 unchanged)
├── examples/example.py
├── prompts/system.md
└── tests/
    ├── test_repl.py         # extended: on_output, handle_command
    └── test_tui.py          # NEW
```

Plus `week1_baseline/bin/python/11_tui` (launcher) and `week1_baseline/bin/ruby/11_tui`.

---

## 5. Ruby → Python semantic gaps new to this step

### 5.1 Bubbletea's Model/Update/View → Textual's App

Ruby implements one object with `init`/`update`/`view` and returns `[model, command]` pairs.
Textual inverts this: widgets own their own rendering, and you mutate state then let the framework
redraw.

| Ruby (Bubbletea) | Python (Textual) |
|---|---|
| `Bubbletea::Runner.new(self, alt_screen: true).run` | `App.run()` (alt-screen is default) |
| `init` → `Bubbletea.tick(0.06) { TickMsg }` | `set_interval(0.06, self._tick)` |
| `update(msg)` case on message class | `on_key`, `on_resize`, plus the interval callback |
| `view` → join four strings | `compose()` yields four widgets, each updated in place |
| `Bubbles::Viewport` | `RichLog` (scrollback, wrapping, `auto_scroll`) |
| `Bubbles::TextArea` | `Input` |
| `Lipgloss::Style#foreground/background/bold` | Textual CSS, or `rich.text.Text` styles |
| `Bubbletea.quit` | `self.exit()` |
| `@dirty` flag + manual `sync_viewport` | Not needed — Textual redraws on mutation |

The `@dirty` bookkeeping and the explicit `view` join both disappear. That is a real simplification,
and the plan should not fight it by emulating Bubbletea's structure in a framework that doesn't want
it.

### 5.2 `Thread#raise(Interrupt)` has **no safe Python equivalent** — the sharpest gap

Ruby's ESC handler is:

```ruby
@turn_thread.raise(Interrupt) if @turn_thread&.alive?
```

Python cannot asynchronously raise an exception in another thread. `ctypes.pythonapi.
PyThreadState_SetAsyncExc` exists, is documented as unsafe, and will not interrupt a thread parked
in a blocking socket read — which is exactly where an agent turn spends its time.

**Proposal: cooperative cancellation.** A `threading.Event` set by the ESC handler and checked by
the agent loop between iterations:

- `Agent.run` takes an optional `cancel` event and checks it at the top of each iteration, raising
  a new `Interrupted` error when set.
- The TUI sets the event on ESC and reports `[interrupted]` exactly as Ruby does.

**Consequence to accept up front:** cancellation lands at the next iteration boundary, not
mid-HTTP-request. Pressing ESC during a slow API call waits for that call to return. Ruby
interrupts immediately. This is a genuine behavioural difference and belongs in the README, not
buried.

This is the one change that reaches outside `tui.py` into `agent.py`. Flagging it because it breaks
the otherwise-clean "step 11 only touches repl + tui" boundary.

### 5.3 Threading: callbacks fire on the worker, widgets live on the UI thread

Ruby runs the turn in `Thread.new` and pushes events onto a `Queue` the UI drains on each tick —
safe because only the tick thread touches widgets.

Textual is asyncio-based and **not** thread-safe for widget mutation. Both `Repl#on_output` and
`Logger#subscribe` fire on the worker thread, so both must marshal:

- Run the turn with `@work(thread=True)` (or `run_worker(..., thread=True)`).
- From the worker, use `app.call_from_thread(...)` or `post_message(...)` — both documented
  thread-safe — rather than touching widgets directly.

Keeping Ruby's `queue.Queue` + drain-on-tick shape also works and stays closer to the reference. I
lean toward keeping the queue: it preserves the Ruby structure and sidesteps the question of which
Textual calls are thread-safe.

`@events.pop(true) rescue nil` → `queue.get_nowait()` inside `except queue.Empty: break`.

### 5.4 Event key types

Ruby's log events use **symbol** keys, so the TUI defensively writes `event[:phase] ||
event["phase"]`. Python's logger emits **string** keys throughout, so this collapses to
`event["phase"]`. Do not port the defensive double-lookup — it is Ruby-specific noise.

Confirmed identical in both trees: subscribers receive the event *before* the `session_id`/`at`
envelope is merged, so `usage` reads the same on both sides.

### 5.5 `Repl#output` indirection

Straight port. `@output_cb` → `self._output_cb`; `output(str)` calls it when set, else `print`.
The one subtlety Ruby already handles: `start` must not print the prompt when a callback is
installed (the TUI draws its own).

### 5.6 The bubbletea patch — not ported, but its bug class is worth a test

The patch fixes `program_poll_event` in the gem's C extension: it read up to 256 bytes, parsed one
key event, and **discarded the remainder** — so fast typing and pastes lost every byte after the
first, Enter included.

Textual's input parsing buffers correctly and has no equivalent defect, so there is nothing to
port. But the *symptom* is a good regression test for any TUI: paste a 43-character string in one
burst and assert 43 characters arrive. Worth having on the Python side precisely because we are not
inheriting the fix.

The second bug the README describes — `charm` loading `ntcharts`, whose Go runtime broke stdin —
is Ruby-only and has no analogue at all.

---

## 6. Implementation steps

### Half A — repair Ruby step 11 (do first)

| # | Task | Detail |
|---|---|---|
| A1 | `chmod +x bin/boukensha` | `check-paths` flags it |
| A2 | Fix `PROMPTS_DIR` | `config.rb`: `../../../prompts` → `../../prompts` (resolves outside the step today) |
| A3 | Fix `BOUKENSHA_DIR` in `examples/example.rb` | `../../../.boukensha` → `../../../../.boukensha` |
| A4 | Create `week1_baseline/bin/ruby/11_tui` | Mirror step 10's launcher, `chmod +x` |
| A5 | `bundle install`; `bundle update mud_manager` | Lockfile pins `mud_manager 0.1.0`, which is gone — same fix as step 10. Installs charm/bubbletea/lipgloss/bubbles |
| A6 | Apply the bubbletea patch | `bundle exec ruby patches/bubbletea/patch_bubbletea.rb`, after A5 |
| A7 | Re-apply step-09/10 work | **Only if Q2 = re-apply.** See §8 |
| A8 | Re-run `check-paths` | Must be clean |
| A9 | Fix `examples/example.rb` header | Says "Step 10", references a nonexistent `examples/demo.rb` |

### Half B — Python port

| # | Task |
|---|---|
| B1 | Copy `python/10_standard_tool_library/` → `python/11_tui/`; bump `version.py` to `0.11.0` |
| B2 | Add the TUI dep to `pyproject.toml` (per Q1); refresh `uv.lock` |
| B3 | Refactor `repl.py`: public `logger`/`context`/`model`/`version`, `on_output`, `handle_command`, `output()`, rebuilt `start` |
| B4 | Extend `repl()` in `__init__.py` with `tui=True`; build `Repl`, hand to `Tui` |
| B5 | Add `cancel` support to `agent.py` + an `Interrupted` error (§5.2) |
| B6 | Write `boukensha/tui.py` |
| B7 | `bin/python/11_tui` launcher with `--no-tui` and `--demo` |
| B8 | Tests: extend `test_repl.py`, add `test_tui.py` |
| B9 | README for the Python step, documenting the ESC difference (§5.2) |

---

## 7. Verification

### 7.1 Offline suite

`./run-tests` from `week1_baseline/python` (per-iteration isolation — every step ships a package
named `boukensha`). Step 10 baseline: 497 tests. Step 11 must not regress any.

New tests, none of which may launch a full-screen app:

- `Repl#on_output` captures everything that would have been printed; nothing reaches stdout
- `handle_command` returns `:quit` / `:command` / `None` for `/exit`, `/help`, `/clear`, and plain text
- `handle_command` routes its output through the callback
- Banner and `run_turn` output both go through `output()`
- TUI event handling: `iteration`, `tool_call`, `tool_result`, `response`, `turn_complete`,
  `turn_interrupted`, `turn_error` each update state correctly — driven by feeding dicts to the
  handler directly, no app instance
- Token accumulation: session and per-turn counters, and `fmt_tokens` (`999` → `"999"`, `1500` → `"1.5k"`)
- Cancellation: setting the event mid-run raises `Interrupted` at the next iteration boundary
- Paste burst: 43 characters in one write yield 43 characters (§5.6)

### 7.2 Parity with Ruby

Both trees, side by side:

- Banner text byte-identical (as achieved for step 10)
- Same tool count (41, if Q2 = re-apply)
- Same `/help` text
- `--no-tui` on both produces the same plain-REPL transcript for a scripted session

### 7.3 Manual TUI check

Not automatable, so it is a checklist: all four zones render; typing is responsive; Enter submits;
`/clear` resets; PgUp/PgDn scroll; Ctrl+C exits; ESC interrupts a running turn; resize reflows;
spinner animates while a turn runs and the status line shows live token counts.

### 7.4 MCP still works

`week1_baseline/mcp/verify-python` (14 checks) and `verify` (35 checks) must both still pass —
they exercise the non-TUI path, which the `Repl` refactor touches.

---

## 8. Known drift in the Ruby step-11 reference

Step 11 branched from upstream's step 10, so it silently reverts six things we fixed. This is the
substance of Q2.

| # | Lost | Consequence |
|---|---|---|
| 1 | `lib/boukensha/mcp/`, `tools/mcp.rb` | No MCP at all; `mcp_servers:` in settings.yaml ignored |
| 2 | `tools/mud.rb` restored (480 lines) | 27 built-in tools duplicating the MCP-served set; double-login |
| 3 | `Tool#required_keys` + `Registry#tool(required:)` | MCP optional params advertised as mandatory (the bug that motivated the member) |
| 4 | `Registry#registered?` | Collision detection gone |
| 5 | Config walk-up to nearest `.boukensha` | Back to `~/.boukensha` only — reverses the change explicitly requested |
| 6 | `client.rb` 401 message | Generic failure instead of "check your API key" |

Independently, `check-paths` reports four failures (A1–A4). Items 1–6 are *design* reverts; A1–A4
are the ordinary copy-forward path regressions this guard exists to catch.

---

## 9. Ruby-side decisions required before porting

1. **Q2** — re-apply steps 09/10 onto step 11, or keep upstream fidelity? Everything about tool
   count, banner text, and cross-tree parity follows from this.
    - Yes
2. **Q3** — restore `/quiet` and `/loud`?
    - lest go with your recomendation
3. Should Ruby's `version.rb` bump land with a rebuilt+reinstalled gem (as for 0.2.0 of
   `mud_manager`), or is the source bump enough for now?
  - up to you, 

---

## 10. Notes

- Nothing here is committed. Per standing instruction, I verify and leave changes in the working
  tree.
- `bin/python/11_tui` should default to the TUI, matching Ruby's `bin/boukensha`, with `--no-tui`
  and `--demo` escape hatches.
- The `patches/` directory has no Python counterpart and should not be copied.
- Effort estimate once questions are answered: Half A is small and mechanical (~1 hour, most of it
  waiting on `bundle install` and the C rebuild). Half B is the real work — `tui.py` is ~300 lines
  and the agent-cancellation change in §5.2 needs care.
