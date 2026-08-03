# 08 · The REPL Loop (Python)

Python port of `week1_baseline/ruby/08_the_repl_loop`.

## What this step adds

| | Step 07 | Step 08 |
|---|---|---|
| Entry point | `boukensha.run(task="…")` | `boukensha.repl()` |
| Turns | one | many |
| History | discarded | accumulates across turns |
| User interaction | none | stdin prompt |

One long-lived `Context` is shared across every turn, and a fresh `Agent` is built per turn. That
is the whole mechanism: because the context persists, turn 2 sees turn 1.

## New primitives

### `boukensha.Repl`

The interactive session loop. Built-in commands, none of which reach the agent:

| Command | Effect |
|---|---|
| `/quiet` | Suppress logging output |
| `/loud` | Re-enable logging output |
| `/clear` | Wipe conversation history (tools stay registered) |
| `/help` | Print the command list |
| `/exit` / `/quit` | Leave the REPL |
| Ctrl-D | EOF — leave the REPL (silently, no "Goodbye.") |
| Ctrl-C | Interrupt — leave the REPL gracefully |

### `boukensha.repl`

`boukensha.run`'s signature minus `task`, since the user supplies tasks interactively. Register
tools through `block=`, then the loop takes over.

```python
def register(dsl):
    @dsl.tool("read_file", description="Read a file from disk",
              parameters={"path": {"type": "string", "description": "File path"}})
    def read_file(*, path):
        return Path(path).read_text()

boukensha.repl(block=register)
```

## Changes from step 07

### `Context.clear_messages`

Wipes `messages` while keeping tools and the system prompt. Backs the `/clear` command.

### `Agent.run` — persists the final reply

Before step 08 the agent returned its final text without adding it to the context. Fine for
one-shot runs, which throw the context away; a REPL needs the full transcript so later turns see
the earlier exchange. All three return paths now append — the completed path and both wind-down
paths.

### `Client` — 401 gets its own message

`authentication failed (401) — check your API key`, instead of the generic non-2xx message that
interpolates the provider's response body. A REPL survives its errors, so the one error a user
can actually fix says what to fix.

### `Config._resolve_dir` — three tiers

`BOUKENSHA_DIR`, then `.boukensha` in the current working directory, then `~/.boukensha`. A REPL
is typically launched from inside a project, so a project-local config now wins over the home
default.

### `Logger.turn` — finally has a caller

Added unused in step 07. The REPL calls it at the start of each turn, so the session log now
carries `{"phase": "turn", "n": N}` markers between turns.

## Code map

```
boukensha/
  repl.py         # NEW — the loop, the built-in commands, the banner
  version.py      # NEW — VERSION, printed in the banner
  __init__.py     # + repl(); exports Repl and VERSION
  context.py      # + clear_messages()
  agent.py        # + the final reply lands in the context
  client.py       # + the 401 branch
  config.py       # + the cwd tier in _resolve_dir
  …               # rest carried forward from step 07
examples/example.py   # the REPL in use
tests/test_repl.py    # NEW — the loop, the commands, the banner, the entry point
```

## Differences from the Ruby original

- **`clear_messages`, not `clear_messages!`.** A bang is not a legal Python identifier, and there
  is no non-mutating counterpart to distinguish it from.
- **`boukensha.repl` is a name collision Ruby does not have.** Ruby keeps the `Boukensha::Repl`
  constant and the `Boukensha.repl` method in separate namespaces. Python has one: `def repl(...)`
  in `__init__.py` rebinds the `boukensha.repl` attribute from the module to the function. It is
  harmless at runtime — `__init__.py` binds the `Repl` class by name first — but tests must reach
  the module through `importlib.import_module("boukensha.repl")`. The filename stays `repl.py` so
  it remains diffable against `repl.rb`. See the port plan §5.1.
- **`block=` instead of `instance_eval`.** Carried forward from step 07; see `run_dsl.py`.
- **`sys.stdin.readline()`, not `input()`.** Ruby's `$stdin.gets` returns `nil` at EOF; an empty
  string from `readline()` is the direct equivalent. `input()` raises `EOFError` instead, which
  would need catching to express the same control flow, and would hide the difference between an
  empty line and EOF.
- **`print(HELP, end="")`.** Ruby's `puts` does not add a second newline to a string that already
  ends in one; Python's `print` always would. Without `end=""` the two trees differ by a blank
  line after `/help`. Found by the parity diff below, not by reading.
- **`max(0, 9 - len(ver))` in the banner padding.** Ruby's `" " * (9 - ver.length)` raises on a
  version longer than 9 characters. The box widens instead of throwing.

## Known defects, carried over from Ruby

- **`Logger.subscribe` still has no caller.** A pub/sub hook with no subscribers anywhere.
- **`LoopError` is still never raised.** `Repl` catches it — the first code in either tree to
  reference it — but nothing raises it, so that arm is unreachable outside the tests.
- **`settings.yaml` carries a `mud` password** that nothing reads.

## Run

```bash
./week1_baseline/bin/python/08_the_repl_loop
```

> **Makes billed API calls, one per turn.** Needs `ANTHROPIC_API_KEY` in `.boukensha/.env`.
> Session logs land in gitignored `.boukensha/sessions/`.

Parity with the Ruby tree is checked by driving both launchers with the same keystrokes. Every
built-in command is handled before the agent runs, so this costs nothing and needs no key:

```bash
diff <(printf '/help\n/exit\n' | ./week1_baseline/bin/ruby/08_the_repl_loop) \
     <(printf '/help\n/exit\n' | ./week1_baseline/bin/python/08_the_repl_loop)
```

Silence means parity. As of the port this is byte-for-byte identical, banner included — the first
step since 03 where a whole run diffs clean, because the interactive surface makes no API call.

## Test

```bash
cd week1_baseline/python
uv run pytest 08_the_repl_loop
```

413 tests, all offline. `test_repl.py` drives the loop by patching `sys.stdin` with a `StringIO`
and swapping in a fake `Agent`, so the full command surface, turn accounting, error recovery, and
banner are covered without a network call.
