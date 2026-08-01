# Python Port Plan — Step 01 · Struct Skeleton

Port `week1_baseline/ruby/01_struct_skeleton` to `week1_baseline/python/01_struct_skeleton`.

**Scope:** week1 only, step 01 only. Builds on the completed step-00 port; reuses the shared
environment at `week1_baseline/python/` (no new venv).

**Prerequisite:** the Ruby reference for this step is currently broken and must be fixed first —
see §9. Without that fix there is no baseline to prove parity against.

---

## 1. Decisions (settled — do not re-litigate)

| Decision | Choice |
|----------|--------|
| Broken Ruby reference | **Fix Ruby first**, then port. One-character path fix (§9). |
| `token_budget` | **Port the code as-is.** `context.rb` has no such field; the README documenting it is stale. Flag, do not implement. |
| Dropped `PROMPTS_DIR` | **Mirror Ruby exactly.** No `PROMPTS_DIR`, no `prompts/` dir. `Context.system` legitimately ends up `None`. |
| `settings.yml` in error text | **Python says `settings.yaml`** (the real filename). Ruby 01 drift flagged separately. |
| Environment | Shared `week1_baseline/python/.venv`. No new dependencies — `dataclasses` is stdlib. |
| Structure | Mirror Ruby 1:1, as in step 00. |

---

## 2. Reference files — what to port

Source of truth is `week1_baseline/ruby/01_struct_skeleton/`.

### New in this step — the actual work

| Read this | Purpose | Becomes |
|---|---|---|
| `lib/boukensha/tool.rb` | `Tool` Struct: name, description, parameters, block | `boukensha/tool.py` |
| `lib/boukensha/message.rb` | `Message` Struct: role, content, tool_use_id | `boukensha/message.py` |
| `lib/boukensha/context.rb` | `Context` class: holds task/system/messages/tools; `register_tool`, `add_message` | `boukensha/context.py` |
| `examples/example.rb` | Smoke test; its output is the parity target | `examples/example.py` |
| `README.md` | Field-by-field intent for each structure. **Note: partly stale — see §8.** | `01_struct_skeleton/README.md` (adapted) |

### Carried forward from step 00 — copy, then apply the noted delta

Each iteration is self-contained (the Ruby tree does the same with its `Gemfile`). Copy from
`week1_baseline/python/00_config/`, then apply the delta:

| File | Delta vs the 00 Python port |
|---|---|
| `boukensha/config.py` | **Remove the `PROMPTS_DIR` constant.** Everything else identical. |
| `boukensha/tasks/base.py` | Identical. (Ruby 01 regressed its error text to `settings.yml`; we keep `settings.yaml`.) |
| `boukensha/tasks/player.py` | Identical. |
| `boukensha/env_file.py` | Identical. |
| `conftest.py` | Identical. |
| `tests/test_config.py` | Drop `test_prompts_dir_constant_points_at_shipped_prompts` — the constant no longer exists. |
| `tests/test_tasks.py` | Keep as-is; `Base`/`Player` are unchanged. |
| `boukensha/__init__.py` | **Extend** — must now also export `Tool`, `Message`, `Context`. |

Confirmed by diffing the Ruby trees: `config.rb` differs from step 00 *only* by the removal of
`PROMPTS_DIR`; `player.rb` is byte-identical; `base.rb` differs only in the two error strings.

### Context only — do not port

- `week1_baseline/ITERATIONS.md` — design constraints.
- `week1_baseline/python/README.md` — the shared-environment contract.
- `docs/plans/python_port/00_config` — the step-00 plan; §5 there still applies in full.

---

## 3. What step 01 actually adds

Three data structures passed around by every later step. No behaviour beyond construction and
display — this step is deliberately inert.

| Structure | Fields | Notes |
|---|---|---|
| `Tool` | `name`, `description`, `parameters`, `block` | `parameters` is a dict of `name → {type, description}`. `block` is the callable invoked when the tool runs; never printed. |
| `Message` | `role`, `content`, `tool_use_id` | `role` is `user` / `assistant` / `tool_result`. `tool_use_id` pairs a result to its call and is omitted from output when absent. |
| `Context` | `task`, `system`, `messages`, `tools` | `task` is the task **class** (e.g. `Player`), not an instance. `messages` is a list, `tools` a dict keyed by tool name. |

`Context` is a plain class (not a Struct) because it has behaviour: `register_tool`,
`add_message`, `tool_count`, `turn_count`.

---

## 4. Target layout

```
week1_baseline/python/01_struct_skeleton/
  README.md
  conftest.py
  boukensha/
    __init__.py
    config.py          # copy-forward, minus PROMPTS_DIR
    env_file.py        # copy-forward
    tool.py            # NEW
    message.py         # NEW
    context.py         # NEW
    tasks/
      __init__.py
      base.py          # copy-forward
      player.py        # copy-forward
  examples/
    example.py
  tests/
    test_config.py     # copy-forward, minus the PROMPTS_DIR test
    test_tasks.py      # copy-forward
    test_tool.py       # NEW
    test_message.py    # NEW
    test_context.py    # NEW
```

No `prompts/` directory — matching Ruby 01. No `pyproject.toml`; the shared one at
`week1_baseline/python/` covers it.

---

## 5. Ruby → Python semantic gaps new to this step

§5 of the step-00 plan still applies (truthiness, path handling, `__str__`/`__repr__`). These are
**additional** and specific to the structs. Every one is verified against the Ruby runtime.

**5.1 — `Struct.new` → `@dataclass`. **
`Struct.new(:role, :content, :tool_use_id)` yields positional construction with `nil` defaults for
omitted trailing args. Use `@dataclass` with `= None` defaults. Do not use `NamedTuple` — Ruby
Structs are mutable and later steps mutate them.

**5.2 — Inclusive ranges are off-by-one. The highest-risk item in this step.**
Ruby's `str[0..40]` is **inclusive** — 41 characters. Python's `[:40]` is 40. Verified:

| Ruby | Length | Python equivalent |
|---|---|---|
| `description.to_s[0..40]` | 41 | `description[:41]` |
| `content.to_s[0..60]` | 61 | `content[:61]` |

Getting this wrong silently truncates one character and breaks parity. The `Tool` line in the
expected output ends `...(north, so` — exactly 41 characters — so the diff will catch it.

**5.3 — Ruby prints symbol arrays as `[:direction]`.**
`parameters.keys` on a Hash with symbol keys renders `[:direction]`; multiple keys render
`[:a, :b]`; empty renders `[]`. Python dict keys are strings and would render `['direction']`.
A small helper must emit the Ruby form. Verified against the Ruby runtime.

**5.4 — `nil.to_s` is `""`, not `"None"`.**
`content.to_s[0..60]` yields `""` for a nil content, and `task&.task_name` interpolates as empty
when `task` is nil. Python must never let `None` reach an f-string here.

**5.5 — Endless methods → properties.**
`def tool_count = @tools.size` and `def turn_count = @messages.size` are Ruby 3 endless methods
called without parens. Use `@property` so call sites stay identical.

**5.6 — Required keyword arguments.**
`def initialize(task:, system: nil)` makes `task` a *required* keyword. Python equivalent is
keyword-only: `def __init__(self, *, task, system=None)`. A positional `Context(Player)` must fail.

**5.7 — Symbols as role values.**
`ctx.add_message(:user, ...)` passes a symbol; it interpolates to `user`. Python passes the plain
string `"user"`. Output is identical; no symbol emulation needed here (unlike §5.3, where the
array *inspect* form is visible).

**5.8 — Mutable default arguments.**
`@messages = []` / `@tools = {}` are per-instance in Ruby. In Python these must be initialised
inside `__init__` (or via `field(default_factory=...)`), never as class-level defaults.

**5.9 — `Struct` equality.**
Ruby Structs compare by value. `@dataclass` gives `__eq__` for free — keep it (do not pass
`eq=False`), so tests can assert on whole objects.

---

## 6. Implementation steps

1. **Fix the Ruby reference** (§9) and capture its output as the parity baseline.
2. **Copy forward** the step-00 Python package into `01_struct_skeleton/`, then apply the §2
   deltas (drop `PROMPTS_DIR`; drop its test).
3. **`boukensha/tool.py`** — `Tool` dataclass + `__str__` with the §5.2 41-char truncation and
   the §5.3 symbol-list helper.
4. **`boukensha/message.py`** — `Message` dataclass + `__str__` with the 61-char truncation and
   the conditional ` [tool_use_id]` tag.
5. **`boukensha/context.py`** — `Context` class: keyword-only `__init__`, `register_tool`,
   `add_message`, `tool_count` / `turn_count` properties, `__str__`.
6. **`boukensha/__init__.py`** — extend exports to `Config`, `Player`, `Tool`, `Message`, `Context`,
   mirroring `lib/boukensha.rb`'s five requires.
7. **`examples/example.py`** — port `example.rb` line-for-line. Note it passes **only**
   `user_prompts_dir` to `system_prompt`, so the result is `None`; do not add `default_prompts_dir`.
8. **Launchers** — `bin/ruby/01_struct_skeleton` and `bin/python/01_struct_skeleton`, matching the
   shape of the existing `00_config` pair.
9. **Tests** — §7.
10. **`README.md`** — adapt, including a differences table as in the step-00 port.

---

## 7. Verification

**Output parity (primary acceptance test).**

```bash
diff <(./week1_baseline/bin/ruby/01_struct_skeleton) <(./week1_baseline/bin/python/01_struct_skeleton)
```

Silence means parity. Target output, captured from the Ruby reference with the §9 fix applied:

```
=== Boukensha Step 1: Struct Skeleton ===

Config:   #<Boukensha::Config dir=/Users/dglebov/claude-code-camp-2026-Q2/.boukensha tasks=player>
Context:  #<Context task=player turns=2 tools=1>
Tool:     #<Tool name=move description=Move the player in a direction (north, so params=[:direction]>
Messages:
  #<Message role=user content=Explore north and tell me what you find....>
  #<Message role=assistant content=Sure, let me head north and take a look....>
```

Three traps visible in that block: the `description=` value stops mid-word at 41 chars (§5.2),
`params=[:direction]` uses Ruby symbol syntax (§5.3), and `task=player` comes from calling
`task_name` on the **class** (§5.6).

**pytest coverage.** Carry forward the 44 step-00 tests (minus the `PROMPTS_DIR` one), and add:

*Tool*
- `__str__` matches the Ruby format exactly, including the 41-char cut
- description shorter than 41 chars is not padded or truncated
- `params=[]` for empty parameters; `[:a, :b]` for two
- `parameters=None` renders `[]` rather than raising
- `block` is callable and invoking it works; it never appears in `__str__`

*Message*
- `__str__` with and without `tool_use_id` (` [toolu_01X]` tag present/absent)
- content longer than 61 chars is cut at exactly 61
- `content=None` renders as empty, not `None`
- value equality (§5.9)

*Context*
- `task` is keyword-only — positional construction raises `TypeError`
- `system` defaults to `None`
- `register_tool` keys the dict by `tool.name`; re-registering the same name replaces
- `add_message` appends in order and threads `tool_use_id` through
- `tool_count` / `turn_count` track their collections
- two Contexts do not share `messages` / `tools` (§5.8)
- `__str__` matches `#<Context task=player turns=N tools=N>`
- `task=None` renders as empty (§5.4)

Run with `uv run pytest 01_struct_skeleton` from `week1_baseline/python`.

---

## 8. Known drift in the Ruby step-01 README

`01_struct_skeleton/README.md` does not match `context.rb`. Port the **code**, not the README.
Recording these so they are not mistaken for port bugs:

- Documents a `token_budget` field on Context; the code has none.
- Shows `#<Context turns=2 tools=1 budget=8192>` plus indented `system:` / `tools:` lines; the
  code prints `#<Context task=player turns=2 tools=1>` and nothing else.
- Omits the `task` field from the Context table, though it is the first thing `to_s` prints.
- Shows `#<Tool ... description="..." ...>` with quotes; the code emits none.
- Run instructions say `./week1_baseline/bin/01_struct_skeleton`; after the bin restructure the
  path is `./week1_baseline/bin/ruby/01_struct_skeleton`. (The Ruby step-00 README is stale the
  same way.)

---

## 9. Ruby-side changes required before porting

Approved in Q1. Both are bug fixes, not redesigns.

**9.1 — Fix the config-dir path (blocking).**
`ruby/01_struct_skeleton/examples/example.rb:2` resolves three levels up to
`week1_baseline/.boukensha`, which does not exist, so `Config` loads no settings, `tasks(:player)`
returns nil, and `Tasks::Base.fetch` raises `NoMethodError: undefined method '[]' for nil`.
Identical to the bug already fixed in step 00.

```diff
-ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../.boukensha", __dir__)
+ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../../.boukensha", __dir__)
```

**9.2 — Add the missing launcher.**
There is no `bin/*/01_struct_skeleton` at all, though the README references one. Create
`bin/ruby/01_struct_skeleton` mirroring `bin/ruby/00_config`.

**9.3 — Optional, flagged not fixed.**
`ruby/01_struct_skeleton/lib/boukensha/tasks/base.rb:9,13` say `settings.yml` in their error text,
but the file is `settings.yaml`. Error-message text only — it cannot affect example output or
parity. Left for you to decide.

---

## 10. Notes

- No new Python dependencies. `dataclasses` is stdlib, so `pyproject.toml` is untouched.
- `Context.system` will be `None` in both trees, because step 01 drops `PROMPTS_DIR` while
  `settings.yaml` still sets `prompt_override.system: true` and no
  `.boukensha/prompts/player/system.md` exists. This is faithful, not a bug in the port.
- `Tool.block` is stored but never invoked in this step; the registry that calls it arrives in
  step 02.
