# Python Port Plan — Step 02 · The Tool Registry

Port `week1_baseline/ruby/02_the_registry` to `week1_baseline/python/02_the_registry`.

**Scope:** week1 only, step 02 only. Builds on the completed step-01 port; reuses the shared
environment at `week1_baseline/python/` (no new venv, no new dependencies).

**Prerequisite:** the Ruby reference for this step is currently broken and must be fixed first —
see §9. Without that fix there is no baseline to prove parity against.

---

## 1. Decisions (settled — do not re-litigate)

| Decision | Choice |
|----------|--------|
| Broken Ruby reference | **Fix Ruby first**, then port. Same one-character path fix as step 01 (§9.1). |
| Ruby block → Python | **Decorator.** `@registry.tool(...)` over a function. Closest analog to a Ruby block; body stays inline and named. Q1-approved. |
| Symbol-key translation in `dispatch` | **No-op in Python — keep the seam anyway.** Document why (§5.2). Do not invent a symbol type. |
| `tools` living on `Context` | **Port as-is.** `ITERATIONS.md` flags this as a known Ruby regression (tools belong on the Registry). Fixing it here would break parity and diverge from every later step. Flag, do not implement. |
| Structure | Mirror Ruby 1:1, as in steps 00 and 01. |
| Environment | Shared `week1_baseline/python/.venv`. Nothing new — `functools` is stdlib. |

---

## 2. Reference files — what to port

Source of truth is `week1_baseline/ruby/02_the_registry/`.

### New in this step — the actual work

| Read this | Purpose | Becomes |
|---|---|---|
| `lib/boukensha/registry.rb` | `Registry` class: `tool` registers, `dispatch` looks up and calls | `boukensha/registry.py` |
| `lib/boukensha/errors.rb` | `UnknownToolError < StandardError` | `boukensha/errors.py` |
| `examples/example.rb` | Smoke test; its output is the parity target | `examples/example.py` |
| `README.md` | Intent behind the registry. **Note: partly stale — see §8.** | `02_the_registry/README.md` (adapted) |

That is the whole of the new work. `registry.rb` is 21 lines and `errors.rb` is 3.

### Carried forward from step 01 — copy, then apply the noted delta

Each iteration is self-contained (the Ruby tree does the same with its `Gemfile`). Copy from
`week1_baseline/python/01_struct_skeleton/`, then apply the delta:

| File | Delta vs the 01 Python port |
|---|---|
| `boukensha/config.py` | Identical. |
| `boukensha/env_file.py` | Identical. |
| `boukensha/tool.py` | Identical. |
| `boukensha/message.py` | Identical. |
| `boukensha/context.py` | Identical. |
| `boukensha/tasks/base.py`, `tasks/player.py`, `tasks/__init__.py` | Identical. |
| `conftest.py` | Identical. |
| `tests/test_config.py`, `test_tasks.py`, `test_tool.py`, `test_message.py`, `test_context.py` | Identical — carry all forward unchanged. |
| `boukensha/__init__.py` | **Extend** — must now also export `Registry` and `UnknownToolError`. |

Confirmed by `diff -ru ruby/01_struct_skeleton ruby/02_the_registry`: apart from the two new
files, the only changes are `README.md`, `examples/example.rb`, and the two extra requires in
`lib/boukensha.rb`. `config.rb`, `context.rb`, `tool.rb`, `message.rb` and both task files are
byte-identical between the two Ruby steps — so the Python copy-forward is byte-identical too.

### Context only — do not port

- `week1_baseline/ITERATIONS.md` §2 — design intent, and the note about the `tools[]` regression.
- `docs/plans/python_port/00_config`, `docs/plans/python_port/01_struct_skeleton` — §5 of each
  still applies in full.

---

## 3. What step 02 actually adds

The agent never calls a tool directly. It emits a structured request (`name`, `args`) and the
Registry looks the tool up and runs it. Two jobs: **store** and **dispatch**.

| Method | Behaviour |
|---|---|
| `Registry(context)` | Holds a reference to the Context. Registration writes through to it. |
| `tool(name, *, description, parameters={})` | Builds a `Tool`, calls `context.register_tool`, returns it. In Python this is a **decorator factory** — see §5.1. |
| `dispatch(name, args={})` | Looks up `context.tools[str(name)]`; raises `UnknownToolError` if absent; otherwise calls the tool's block with `**args`. |

`UnknownToolError` exists because a harness needs explicit error boundaries — an unrecognised
tool name must never silently fail.

---

## 4. Target layout

```
week1_baseline/python/02_the_registry/
  README.md
  conftest.py                # copy-forward
  boukensha/
    __init__.py              # extended: + Registry, UnknownToolError
    config.py                # copy-forward
    env_file.py              # copy-forward
    tool.py                  # copy-forward
    message.py               # copy-forward
    context.py               # copy-forward
    errors.py                # NEW
    registry.py              # NEW
    tasks/
      __init__.py            # copy-forward
      base.py                # copy-forward
      player.py              # copy-forward
  examples/
    example.py               # rewritten for this step
  tests/
    test_config.py           # copy-forward
    test_tasks.py            # copy-forward
    test_tool.py             # copy-forward
    test_message.py          # copy-forward
    test_context.py          # copy-forward
    test_registry.py         # NEW (covers errors.py too)
```

No `pyproject.toml`; the shared one at `week1_baseline/python/` covers it.

---

## 5. Ruby → Python semantic gaps new to this step

§5 of the step-00 and step-01 plans still applies. These are **additional** and specific to the
registry. Every one is verified against the Ruby runtime.

**5.1 — `&block` → a decorator. The design decision of this step.**
Ruby's `def tool(name, description:, parameters: {}, &block)` captures a trailing `do |direction:|
… end`. Python has no block syntax. `tool` therefore returns a decorator that registers the
wrapped function and **returns the function unchanged**, so the name stays bound to a callable:

```python
def tool(self, name, *, description, parameters=None):
    def decorator(block):
        self._context.register_tool(Tool(str(name), description, parameters or {}, block))
        return block
    return decorator
```

Consequence to note in the README: Ruby's `tool` returns the `Tool`; the Python version returns a
decorator, and after application the name is bound to the function. The example uses neither
return value, so parity is unaffected.

**5.2 — `transform_keys(&:to_sym)` is a no-op in Python.**
`tool.block.call(**args.transform_keys(&:to_sym))` exists because the API hands back string-keyed
JSON while Ruby blocks want symbols. Python keyword arguments *are* strings, so
`tool.block(**args)` is already correct. Keep `dispatch` as the single translation seam and say in
a comment why it is empty here — the README makes a teaching point of this gotcha and a reader
comparing the two files will look for it.

One real difference: Ruby's `to_sym` accepts any string, so a key like `"tool-name"` becomes a
usable symbol. Python raises `TypeError` when `**` is given a key that is not a valid identifier
and the callable has no `**kwargs`. Not reachable from the example; worth one line of comment.

**5.3 — Blocks with required keyword args → keyword-only functions.**
`do |direction:| … end` requires the `direction:` keyword and rejects extras. `def move(*,
direction)` behaves identically: missing key → `TypeError`, unexpected key → `TypeError`,
positional call → `TypeError`. Write example tools keyword-only, not positionally.

Note this differs from Python 01's `examples/example.py`, which passed a *positional* lambda
(`lambda direction: …`) to `Tool`. Step 02 moves to keyword-only because that is what `dispatch`
does via `**args`. `tool.py` itself is unchanged.

**5.4 — `StandardError` → `Exception`.**
`class UnknownToolError < StandardError; end` becomes `class UnknownToolError(Exception): pass`.
`Exception`, not `BaseException` — Ruby's `StandardError` is the rescuable-by-default tier, and
`BaseException` would sit alongside `KeyboardInterrupt`/`SystemExit`.

`raise UnknownToolError, "No tool registered as '#{name}'"` →
`raise UnknownToolError(f"No tool registered as '{name}'")`. Interpolate the **original** `name`,
not `str(name)`, so a symbol-ish input renders the way it was passed.

**5.5 — Mutable default arguments.**
Ruby's `parameters: {}` and `args = {}` allocate fresh each call. Python defaults are evaluated
once at definition time — use `None` sentinels (`parameters=None` → `parameters or {}`,
`args=None` → `args or {}`). `dispatch("flee")` with no args is exercised by the example, so this
path is live.

**5.6 — `name.to_s` on lookup and registration.**
Both `tool` and `dispatch` call `name.to_s`, so `:move` and `"move"` hit the same entry. Python
uses `str(name)` in both places for the same tolerance. `Context.tools` stays keyed by the string.

**5.7 — `rescue` → `except`, and the message.**
`rescue Boukensha::UnknownToolError => e` … `e.message` becomes
`except UnknownToolError as e:` … `{e}`. `str()` on a single-argument Exception yields exactly the
message, so the output line matches without extra work.

**5.8 — Registration order is display order.**
`ctx.tools.each_value` iterates a Ruby Hash in insertion order; Python dicts do the same. `move`
then `shout`, in both trees. No sorting anywhere.

---

## 6. Implementation steps

1. **Fix the Ruby reference** (§9) and capture its output as the parity baseline.
2. **Copy forward** the step-01 Python package into `02_the_registry/` verbatim — all of
   `boukensha/`, `conftest.py`, and all five test modules.
3. **`boukensha/errors.py`** — `UnknownToolError(Exception)`.
4. **`boukensha/registry.py`** — `Registry` with `tool` (decorator factory, §5.1) and `dispatch`
   (§5.2, §5.5, §5.6).
5. **`boukensha/__init__.py`** — extend exports to `Config`, `Player`, `Tool`, `Message`,
   `Context`, `Registry`, `UnknownToolError`, mirroring `lib/boukensha.rb`'s seven requires.
6. **`examples/example.py`** — port `example.rb` line-for-line: build config → context → registry,
   register `move` and `shout` via the decorator, print the four blocks, dispatch twice, then
   dispatch `flee` inside a `try/except`. Keep Ruby's exact spacing (`Config:` is followed by two
   spaces, `Context:` by one).
7. **Launchers** — `bin/ruby/02_the_registry` and `bin/python/02_the_registry`, matching the shape
   of the existing `01_struct_skeleton` pair.
8. **Tests** — §7.
9. **`README.md`** — adapt, including a differences table as in the previous ports. Call out the
   decorator (§5.1) and the empty translation seam (§5.2) explicitly; both are places where a
   reader diffing against Ruby will expect an explanation.
10. **`week1_baseline/python/README.md`** — add step 02 to the Iterations table.

---

## 7. Verification

**Output parity (primary acceptance test).**

```bash
diff <(./week1_baseline/bin/ruby/02_the_registry) <(./week1_baseline/bin/python/02_the_registry)
```

Silence means parity. Target output, captured from the Ruby reference with the §9.1 fix applied:

```
=== BOUKENSHA Step 2: Tool Registry ===

Config:  #<Boukensha::Config dir=/Users/dglebov/claude-code-camp-2026-Q2/.boukensha tasks=player>
Context: #<Context task=player turns=0 tools=2>
Tools:
  #<Tool name=move description=Move the player in a direction (north, so params=[:direction]>
  #<Tool name=shout description=Shout a message so everyone in the zone c params=[:message]>

Dispatching 'shout' with message='dragon spotted'...
Result: DRAGON SPOTTED

Dispatching 'move' with direction='north'...
Result: You move north into a torch-lit corridor.

UnknownToolError caught: No tool registered as 'flee'
```

Traps visible in that block: both `description=` values stop mid-word at 41 characters (step-01
§5.2), `params=[:direction]` uses Ruby symbol syntax (step-01 §5.3), `turns=0` because this
example adds no messages, and the tools list is in registration order (§5.8).

**pytest coverage.** Carry forward the step-01 suite unchanged, and add `tests/test_registry.py`:

*Registration*
- `tool(...)` returns a decorator; applying it registers into `context.tools` keyed by name
- the decorator returns the original function, so the module-level name stays callable
- the registered object is a `Tool` with the given `description` and `parameters`, and `block` is
  the decorated function
- `parameters` omitted defaults to `{}` — and two registrations do not share one dict (§5.5)
- a symbol-ish/non-string `name` is stored as `str(name)` (§5.6)
- re-registering the same name replaces the entry (inherited `Context.register_tool` behaviour)

*Dispatch*
- returns the block's return value, with string-keyed args passed through as keywords (§5.2)
- `dispatch("flee")` with no args at all raises rather than `TypeError`-ing on the default
- a tool taking no parameters dispatches with no args
- unknown name raises `UnknownToolError` with message `No tool registered as 'flee'`
- `UnknownToolError` is catchable as `Exception` (§5.4)
- a missing required arg raises `TypeError` from the block, not `UnknownToolError` — the error
  boundary is about the *name*, not the arguments
- lookup accepts the non-string form of a registered name (§5.6)

Run with `uv run pytest 02_the_registry` from `week1_baseline/python`, then `./run-tests` to
confirm steps 00–02 all still pass, and `uv run ruff check .`.

---

## 8. Known drift in the Ruby step-02 README

Port the **code**, not the README. Recording these so they are not mistaken for port bugs:

- The Expected Output block shows `#<Context turns=0 tools=2 budget=8192>`; the code prints
  `#<Context task=player turns=0 tools=2>`. Same stale `budget` field flagged in step 01.
- The Expected Output block omits the `Config:` line, which the example does print.
- Tool examples elsewhere in the README show `description="…"` with quotes; the code emits none.
- Run instructions say `./week1_baseline/bin/01_the_registry` — wrong step number *and* wrong path.
  After the bin restructure it is `./week1_baseline/bin/ruby/02_the_registry`.
- `ITERATIONS.md` §2 states that `tools[]` should live on the Registry, not the Context — an
  acknowledged regression in the Ruby code. Per §1 the port mirrors the code as it stands.

---

## 9. Ruby-side changes required before porting

Both are bug fixes, not redesigns — the same pair approved for step 01.

**9.1 — Fix the config-dir path (blocking).**
`ruby/02_the_registry/examples/example.rb:1` resolves three levels up to
`week1_baseline/.boukensha`, which does not exist, so `Config` loads no settings, `tasks(:player)`
returns nil, and `Tasks::Base.fetch` raises `NoMethodError: undefined method '[]' for nil`.
Confirmed by running it. Identical to the bug already fixed in steps 00 and 01.

```diff
-ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../.boukensha", __dir__)
+ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../../.boukensha", __dir__)
```

(Step 02 did fix the *ordering* bug from step 01 — the `ENV` line now precedes the `require` — but
kept the wrong level count.)

**9.2 — Add the missing launcher.**
There is no `bin/ruby/02_the_registry`, though the README references one. Create it mirroring
`bin/ruby/01_struct_skeleton`.

**9.3 — Optional, flagged not fixed.**
`ruby/02_the_registry/lib/boukensha/tasks/base.rb:9,13` still say `settings.yml` in their error
text, but the file is `settings.yaml`. Carried forward unchanged from step 01, where it was also
left alone. Error-message text only — it cannot affect parity.

---

## 10. Notes

- No new Python dependencies. `pyproject.toml` is untouched.
- The Python `dispatch` will contain a translation step that does nothing. That is deliberate and
  must be commented, not deleted — it is the hook every later step's tool-calling path runs
  through, and the Ruby README teaches it as a production gotcha.
- `Context.system` is still `None` in both trees, for the reason given in the step-01 plan (§10).
  This step's example never prints it.
- Step 02 is the first step where `Tool.block` is actually invoked. Step 01 stored it and never
  called it.
