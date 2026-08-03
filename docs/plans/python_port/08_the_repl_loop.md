# Python Port Plan — Step 08 · The REPL Loop

Port `week1_baseline/ruby/08_the_repl_loop` to `week1_baseline/python/08_the_repl_loop`.

**Scope:** week1 only, step 08 only. Builds on the completed step-07 port; reuses the shared
environment at `week1_baseline/python/` (no new venv, no new dependencies).

**Prerequisites:** the Ruby reference was fixed on 2026-08-03 (§9) and runs end to end.

The first step whose entry point is *interactive*. That changes what "parity" means and what the
tests have to fake: stdin becomes an input, and the whole built-in command surface runs without
ever reaching the network — which makes this the first step since 03 whose console output can be
diffed byte-for-byte against Ruby for free.

---

## 1. Decisions (settled — do not re-litigate)

| Decision | Choice |
|----------|--------|
| Broken Ruby reference | **Fixed first** — `check-paths` caught all three failures again, the eighth consecutive occurrence (§9). |
| `Boukensha::Repl` / `Boukensha.repl` collision | **Keep `repl.py`; accept the attribute rebind.** Ruby has separate constant and method namespaces; Python does not. `def repl(...)` in `__init__.py` shadows the submodule attribute. Harmless at runtime; tests reach the module via `importlib.import_module` (§5.1). |
| `clear_messages!` | **`clear_messages`.** Bang is not a legal Python identifier and there is no non-mutating counterpart to distinguish it from. |
| Reading stdin | **`sys.stdin.readline()`**, not `input()`. Ruby's `gets` returns `nil` at EOF; `""` is the direct equivalent. `input()` raises `EOFError`, which would need catching to express the same control flow (§5.2). |
| `puts` vs `print` | **`print(HELP, end="")`.** Ruby's `puts` suppresses a second newline on a string that already ends in one. Without this the trees differ by a blank line (§5.3). |
| Banner padding | **`max(0, 9 - len(ver))`.** Ruby raises on a version longer than 9 chars; the box widens instead (§5.4). |
| `Agent` seam for tests | **Patch `Agent` in the repl module.** The REPL constructs one per turn; that is the only seam needed. No network stub required anywhere in `test_repl.py`. |
| Structure | Mirror Ruby 1:1, including file names. |
| Environment | Shared `.venv`. No new dependencies. |

---

## 2. Reference files — what to port

Source of truth is `week1_baseline/ruby/08_the_repl_loop/`. Delta established with a whole-tree
`diff -rq` against `07_the_run_dsl`.

### New in this step

| Read this | Purpose | Becomes |
|---|---|---|
| `lib/boukensha/repl.rb` | ~140 lines. The loop, the six built-in commands, the banner | `boukensha/repl.py` |
| `lib/boukensha/version.rb` | 1 constant, printed in the banner | `boukensha/version.py` |
| `lib/boukensha.rb` → `self.repl` | `self.run` minus `task:`, ending in `Repl(...).start()` | `boukensha/__init__.py` → `repl()` |
| `examples/example.rb` | Two file tools, then the loop takes over | `examples/example.py` |
| `README.md` | Step README | `08_the_repl_loop/README.md` (adapted) |

### Changed vs step 07

| File | Delta |
|---|---|
| `boukensha/context.py` | **`clear_messages()`** — empties `messages`, keeps tools and system prompt. |
| `boukensha/agent.py` | **The final reply is appended to the context** in all three return paths (completed, wind-down success, wind-down `ApiError` fallback). First change to `agent.py` since step 06. |
| `boukensha/client.py` | **A 401 branch** ahead of the generic non-2xx raise: `authentication failed (401) — check your API key`. |
| `boukensha/config.py` | **`_resolve_dir` gains a middle tier** — `BOUKENSHA_DIR`, then `.boukensha` in the cwd, then `~/.boukensha`. |
| `boukensha/logger.py` | **No change** — but `turn(n=)`, dead since step 07, finally acquires a caller. |

### Carried forward from step 07 — unchanged

Everything else, `run_dsl.py` and `run()` included. `repl()` does not replace `run()`; both ship.

---

## 3. What step 08 actually adds

One idea: **the context outlives the turn.**

Steps 04–07 built a `Context`, ran an agent once, and threw it away. `Repl` keeps it and builds a
new `Agent` per turn against the same context. Everything else follows from that:

- `Agent.run` must record its final reply, or turn 2 sees a transcript that ends with turn 1's
  question and no answer. This is the one library change with real consequences.
- `/clear` needs `Context.clear_messages` — a way to drop history *without* dropping the tools,
  which live on the same object.
- `Logger.turn` becomes meaningful: it marks where one turn's events end and the next begin in a
  session log that now holds many turns.

The banner and the command table are surface. The transcript is the step.

---

## 4. Target layout

```
week1_baseline/python/08_the_repl_loop/
  boukensha/
    repl.py                # NEW
    version.py             # NEW
    __init__.py            # + repl(); exports Repl, VERSION
    context.py             # + clear_messages()
    agent.py               # + final reply appended, 3 sites
    client.py              # + 401 branch
    config.py              # + cwd tier in _resolve_dir
    logger.py              # unchanged; turn() finally called
    …                      # rest copy-forward
  examples/example.py      # NEW — the REPL in use
  tests/
    test_repl.py           # NEW — loop, commands, banner, entry point
    test_context.py        # + clear_messages
    test_agent.py          # + reply persistence; 2 existing assertions shift by one
    test_client.py         # + 401
    test_config.py         # + the three tiers
    …
```

Plus `week1_baseline/bin/python/08_the_repl_loop`.

---

## 5. Ruby → Python semantic gaps new to this step

### 5.1 `Boukensha::Repl` and `Boukensha.repl` cannot coexist — the central decision

Ruby resolves `Boukensha::Repl` (constant) and `Boukensha.repl` (method) through separate
namespaces. Python has one namespace per module. `from .repl import Repl` binds the submodule as
`boukensha.repl`; the later `def repl(...)` rebinds that attribute to the function.

At runtime this is harmless — `Repl` is already bound by name before the rebind, so `repl()` can
still construct it. The cost is reflection: `monkeypatch.setattr("boukensha.repl.Agent", …)`
reaches the *function*, not the module, and fails.

Three options were considered:

1. **Rename the module** (`repl_loop.py`). Kills the collision, breaks file-for-file
   correspondence with `repl.rb` — the property that makes the two trees diffable step by step.
2. **Rename the function.** Breaks the API mirror; `Boukensha.repl` is the documented entry point.
3. **Keep both names; reach the module through `sys.modules` in tests.** Chosen.

`importlib.import_module("boukensha.repl")` reads `sys.modules` first, which still holds the real
module object. One line at the top of `test_repl.py`; nothing in the library bends.

### 5.2 `$stdin.gets` → `sys.stdin.readline()`, not `input()`

Ruby's `gets` returns `nil` at EOF, which the loop tests with `break unless input`. Python's
`sys.stdin.readline()` returns `""` at EOF — the same sentinel shape, testable with the same
single branch. `input()` raises `EOFError` instead, forcing a `try/except` around the read and
splitting one branch into two. It would also strip the trailing newline, hiding the distinction
between "empty line" and "EOF" that the loop depends on.

### 5.3 `puts` does not double a trailing newline; `print` does

`puts` on a string already ending in `\n` writes it unchanged. `print` always appends. Ruby's
`HELP` heredoc ends in a newline, so `puts HELP` and `print(HELP)` differ by one blank line.

This was caught by the §7.2 diff, not by reading — it is invisible in isolation and only shows up
against the Ruby output. `print(HELP, end="")`. The banner does **not** need this: its heredoc
ends with a blank line, so Ruby emits `\n\n` and Python's `print` on a single-`\n` string produces
the same two bytes.

### 5.4 The banner padding raises in Ruby

`" " * (9 - ver.length)` raises `ArgumentError: negative argument` once a version exceeds nine
characters. Python's `" " * -1` returns `""` silently, which would widen the box rather than
crash. Neither behaviour is right, but a REPL that refuses to start over its own version string
is worse than a ragged box. `max(0, 9 - len(ver))`, and a test pinning it.

### 5.5 `import boukensha` inside the command branches

`__init__.py` imports `repl.py` while `__init__.py` is still executing, so a module-scope
`import boukensha` in `repl.py` is circular. `/quiet` and `/loud` import at call time instead.
The alternative — passing the module-state setters in as constructor arguments — would diverge
from Ruby's `Boukensha.quiet!` for no gain.

---

## 6. Implementation steps

1. **Verify the Ruby baseline** — `./week1_baseline/bin/ruby/check-paths`, then drive the REPL
   with piped keystrokes and keep the output. (§9 is already applied.)
2. **Copy forward** step 07 into `08_the_repl_loop/`, repointing docstrings at
   `ruby/08_the_repl_loop`. Confirm the copy is green before changing anything.
3. **`boukensha/context.py`** — `clear_messages()`.
4. **`boukensha/agent.py`** — append the final reply at all three return sites.
5. **`boukensha/client.py`** — the 401 branch.
6. **`boukensha/config.py`** — the cwd tier in `_resolve_dir`.
7. **`boukensha/version.py`** — `VERSION`.
8. **`boukensha/repl.py`** — the class, per §5.1–5.5.
9. **`boukensha/__init__.py`** — `repl()`, mirroring `run()`'s order of operations with the same
   `logger = None` guard, plus `except KeyboardInterrupt`.
10. **`examples/example.py`** — the two file tools, then `boukensha.repl(block=register)`.
11. **Launcher** — `week1_baseline/bin/python/08_the_repl_loop`.
12. **Tests** — §7.
13. **READMEs** — step README, plus a row in `week1_baseline/python/README.md`.

---

## 7. Verification

### 7.1 Offline suite

*`Repl`* (`test_repl.py`) — `sys.stdin` patched with a `StringIO`, `Agent` patched with a fake.
Nothing here touches the network.

- **Leaving:** `/exit` and `/quit` both print `Goodbye.`; EOF leaves *without* one; input after
  `/exit` is never read
- **Commands:** `/help` lists all five; no command reaches the agent; blank and whitespace-only
  lines are skipped; input is stripped before dispatch, so `  /exit  ` exits
- **`/quiet` and `/loud`** toggle module state and announce themselves
- **`/clear`** empties history, keeps tools, and resets the turn counter to 0
- **Turns:** a normal line runs one turn and prints the reply; **history accumulates across
  turns** — the step's whole point, asserted on the message sequence; a command between turns does
  not advance the counter
- **Errors:** `ApiError` and `LoopError` are reported and the loop survives to reach `/exit`; a
  failed turn still counts as a turn
- **Banner:** API key present/absent (`None`, `""`, `"   "`); config dir missing vs present;
  version and provider text; a long version does not raise (§5.4)

*`repl()`* (`test_repl.py`) — with `Repl` patched out, so nothing starts
- wiring resolves from settings: model, provider, `config_dir`, `version`
- the block's tools reach the context; the transcript starts empty
- `task=` is rejected — it is `run`'s argument, not this one
- an unknown backend raises `ValueError`
- the logger is closed on the way out
- **`KeyboardInterrupt` is swallowed and prints `Interrupted.`** — Ruby's `rescue Interrupt`

*`Context`* — `clear_messages` drops history, keeps tools/system/task, is idempotent, and leaves
the object usable afterwards.

*`Agent`* — the final text is appended once, on the completed path and the wind-down path, and
lands *after* the tool turns. **Two existing tests index `messages[-1]` and legitimately shift by
one** — update them with a comment naming step 08, do not weaken them.

*`Client`* — 401 gets the new message; the body is not leaked into it; 403 keeps the generic one.

*`Config`* — all three tiers, plus a cwd `.boukensha` that is a *file* rather than a directory,
which must fall through to the home default.

```bash
cd week1_baseline/python && ./run-tests
```

### 7.2 Console parity (offline, free)

New this step and better than every previous step's: because every built-in command is handled
before the agent runs, a whole session can be driven and diffed without a key or a billed call.

```bash
diff <(printf '/help\n/exit\n' | ./week1_baseline/bin/ruby/08_the_repl_loop) \
     <(printf '/help\n/exit\n' | ./week1_baseline/bin/python/08_the_repl_loop)
diff <(printf '\n/quiet\n/loud\n/clear\n' | ./week1_baseline/bin/ruby/08_the_repl_loop) \
     <(printf '\n/quiet\n/loud\n/clear\n' | ./week1_baseline/bin/python/08_the_repl_loop)
```

Both must be silent — banner included. This is what caught §5.3.

### 7.3 Live run (both trees)

One turn each, same prompt, then compare the session logs structurally as in steps 06–07: same
phase sequence, same key vocabulary, same `session_start` snapshot keys. Step 08 adds `"turn"`
phases — assert they appear, one per turn, numbered from 1.

---

## 8. Known drift in the Ruby step-08 reference

- **`Logger#subscribe` still has no caller.** Dead since step 07.
- **`LoopError` is still never raised.** `Repl` *rescues* it — the first reference to it anywhere
  in either tree — but nothing raises it, so the arm is unreachable. Mirrored anyway; the tests
  cover it by raising one directly.
- **The README's sample banner was wrong.** It showed a two-line `BOUKENSHA REPL — MUD assistant`
  box that the code has never printed. Corrected in the Ruby README as part of §9.
- **`settings.yaml` carries a `mud` password** that nothing reads. Unchanged since step 00.

---

## 9. Ruby-side changes required before porting

**Applied 2026-08-03.** `check-paths` caught all three on its first run against step 08 — the
**eighth** consecutive occurrence of this regression:

```
FAIL 08_the_repl_loop  BOUKENSHA_DIR -> week1_baseline/.boukensha   (does not exist)
FAIL 08_the_repl_loop  PROMPTS_DIR   -> week1_baseline/ruby/prompts (does not exist)
FAIL 08_the_repl_loop  launcher missing or not executable: bin/ruby/08_the_repl_loop
```

Fixed: `examples/example.rb:1` three `..` → four; `lib/boukensha/config.rb:13` three → two;
`bin/ruby/08_the_repl_loop` created at mode 755.

Also corrected, outside the checker's remit:

- **README step numbers were off by one** in both 07 and 08 — `07_the_run_dsl` titled itself
  "Step 6" and `08_the_repl_loop` inherited the shift. Another copy-forward miscount, in prose
  rather than in paths.
- **The README's run block named `cd 07_the_repl_loop` and `examples/step7.rb`**, neither of
  which exists.
- **The example's tool sandbox pointed at `../../07_the_run_dsl`**, so step 08's REPL browsed
  step 07's source.

The step had never been committed; it entered git already fixed.

---

## 10. Notes

- §5.1 is the second place the Python tree cannot mirror Ruby structurally (after step 07's
  `instance_eval`). Both times the resolution was to keep the *file* correspondence and absorb
  the cost in the tests. Put the reasoning in the module docstring, not only here.
- §5.3 is the kind of defect only a diff finds. It is one blank line, invisible in isolation, and
  it would have shipped. §7.2 exists because of it — and it costs nothing to run, so it should
  run on every step from here on.
- `Agent.run` appending its own reply is the first change to `agent.py` since step 06, and it
  breaks two existing tests *correctly*. A test that indexes from the end of a growing collection
  is measuring the collection's length as much as its contents; the fix is to say which element
  is meant, not to loosen the assertion.
- The REPL is the first component whose input is a *stream*. Patching `sys.stdin` with a
  `StringIO` and the `Agent` with a fake covers the entire surface offline — worth remembering
  for step 09 if it stays interactive.
