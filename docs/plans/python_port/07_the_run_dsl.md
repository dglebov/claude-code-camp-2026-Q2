# Python Port Plan — Step 07 · The Run DSL

Port `week1_baseline/ruby/07_the_run_dsl` to `week1_baseline/python/07_the_run_dsl`.

**Scope:** week1 only, step 07 only. Builds on the completed step-06 port; reuses the shared
environment at `week1_baseline/python/` (no new venv, no new dependencies).

**Prerequisites:** none — the Ruby reference was fixed on 2026-08-03 (§9) and runs end to end.

Small in volume, large in consequence. `RunDSL` is **13 lines**; `Boukensha.run` is ~80. But this
is the first step whose central mechanism — Ruby's `instance_eval` — **has no Python equivalent at
all**, so it is the first step where the two trees cannot be structurally identical.

---

## 1. Decisions (settled — do not re-litigate)

| Decision | Choice |
|----------|--------|
| Broken Ruby reference | **Already fixed** — the `check-paths` guard caught all three failures on its first real use (§9). |
| `instance_eval(&block)` | **Explicit receiver.** `run(..., block=fn)` where `fn` takes the `RunDSL` as its one argument. Python cannot rebind `self` inside a caller's function; every alternative is worse (§5.1). This is a **deliberate, documented API divergence** — the first in seven steps. |
| `RunDSL.tool` | **A decorator**, matching `Registry.tool`, which it delegates to. The Ruby takes a block; the Python takes the decorated function. |
| `LoopError` | **Re-add it.** Added unused in 05, removed in 06, restored in 07 — still never raised. Mirror each state change in sequence (§8). |
| `mud_*` config readers | **Restore them.** Removed in 06, back in 07, still unreferenced. Same treatment. |
| `Logger#turn` and `#subscribe` | **Mirror, flag.** Both added this step, neither called by anything — `agent.rb` is byte-identical to step 06's. |
| Structure | Mirror Ruby 1:1 **except** the DSL entry point, which cannot be mirrored. |
| Environment | Shared `.venv`. No new dependencies. |

---

## 2. Reference files — what to port

Source of truth is `week1_baseline/ruby/07_the_run_dsl/`. Delta established with a whole-tree
`diff -rq`.

### New in this step

| Read this | Purpose | Becomes |
|---|---|---|
| `lib/boukensha/run_dsl.rb` | 13 lines. The object `self` becomes inside a `run` block; exposes only `tool` | `boukensha/run_dsl.py` |
| `lib/boukensha.rb` → `self.run` | ~80 lines. Wires config → context → registry → backend → builder → client → logger → agent, then runs it | `boukensha/__init__.py` → `run()` |
| `examples/example.rb` | Collapses ~80 lines of wiring into one `Boukensha.run` call | `examples/example.py` |
| `README.md` | Step README | `07_the_run_dsl/README.md` (adapted) |

### Changed vs step 06

| File | Delta |
|---|---|
| `boukensha/logger.py` | **`turn(n=)`** — writes `{"phase": "turn", "n": n}`. **`subscribe(block)`** — appends to a lazily-created `_subscribers` list, each called with every event from `_write_log`. Neither has a caller. |
| `boukensha/errors.py` | **Re-add `LoopError`.** |
| `boukensha/config.py` | **Restore the four `mud_*` readers** (`mud_host` defaulting to `"localhost"`, `mud_port` to `4000`, `mud_username`/`mud_password` to `None`). Restore their tests too — they were deleted in the step-06 port. |
| `boukensha/context.py` | **No change.** Ruby's diff is whitespace realignment plus a *removed* trailing newline. |

### Carried forward from step 06 — unchanged

Everything else, including **`agent.py`, which is byte-identical to step 06's** — worth stating
explicitly, because `Logger#turn` looks like it should have a caller in the agent and does not.

---

## 3. What step 07 actually adds

Steps 00–06 built primitives and made the example wire them together by hand. Step 07 adds the
front door.

**Before** (step 06's example, ~80 lines): construct `Config`, read task settings, resolve the
system prompt, build a `Context`, build a `Registry`, branch five ways on provider to build a
backend, build a `PromptBuilder`, a `Client`, a `Logger`, an `Agent`, register tools, append the
user message, call `run`.

**After** (step 07's example, ~20 lines):

```ruby
result = Boukensha.run(task: "Read the README.md and summarise it") do
  tool "read_file",
    description: "Read a file from disk",
    parameters:  { path: { type: "string", description: "File path" } } do |path:|
    File.read(path)
  end
end
```

Everything else is defaulted from `settings.yaml` and `.env`, and every default is overridable by
keyword: `system:`, `model:`, `backend:`, `api_key:`, `ollama_host:`, `log:`,
`max_output_tokens:`.

Two supporting pieces:

**`RunDSL`** is deliberately tiny — it exposes `tool` and nothing else, so the block cannot reach
into the rest of the object graph. In Ruby that containment comes from `instance_eval` rebinding
`self`; in Python it comes from the block only ever receiving the `RunDSL` (§5.1).

**A richer `session_start` snapshot.** `run` passes task, `max_iterations`, `max_output_tokens`,
model and provider into `Logger.new(snapshot:)`, so the first line of every log now records the
whole effective configuration:

```json
{"phase":"session_start","task":"player","max_iterations":25,"max_output_tokens":1024,
 "model":"claude-sonnet-4-6","provider":"anthropic","session_id":"...","at":"..."}
```

---

## 4. Target layout

```
week1_baseline/python/07_the_run_dsl/
  boukensha/
    __init__.py            # + run(), RunDSL export; module state carried forward
    run_dsl.py             # NEW — small
    logger.py              # + turn(), subscribe()
    errors.py              # + LoopError (again)
    config.py              # + mud_* readers (again)
    …                      # rest copy-forward, agent.py included
  examples/example.py      # NEW — the DSL in use
  tests/
    test_run.py            # NEW — the wiring
    test_run_dsl.py        # NEW — the DSL surface
    test_logger.py         # + turn/subscribe
    test_config.py         # + mud_* (restored)
    …
```

Plus `week1_baseline/bin/python/07_the_run_dsl`.

---

## 5. Ruby → Python semantic gaps new to this step

### 5.1 `instance_eval` has no Python equivalent — the central decision

```ruby
RunDSL.new(registry).instance_eval(&block) if block
```

`instance_eval` re-binds `self` inside the caller's block, so a bare `tool "..."` resolves to
`RunDSL#tool`. **Python has no way to do this.** A function's name resolution is fixed at compile
time; there is no supported mechanism to inject a receiver into a caller's function body. Every
workaround (rewriting `func.__globals__`, `exec` against a custom namespace, frame hacking) is
fragile, unreadable, and breaks tooling.

**Decision: the block takes the DSL as an argument.**

```python
def register(dsl):
    @dsl.tool(
        "read_file",
        description="Read the contents of a file from disk",
        parameters={"path": {"type": "string", "description": "The file path to read"}},
    )
    def read_file(*, path):
        return (base_dir / path).read_text()

result = boukensha.run(task="Read the README.md and summarise it", block=register)
```

Alternatives considered and rejected:

| Alternative | Why not |
|---|---|
| `with boukensha.run(...) as dsl:` | `run` returns the agent's result; a context manager cannot also be the return value without contortions, and the tool registration would have to happen *before* the call it is syntactically inside. |
| Mutate `block.__globals__` to inject `tool` | Leaks into the module's namespace for the duration, is not thread-safe, and breaks if the block is a closure or a lambda. Genuinely dangerous. |
| `run(task=..., tools=[Tool(...), ...])` | Drops the DSL entirely. Simpler, but abandons the step's actual subject. |

**One thing that ports for free:** Ruby's block closes over enclosing locals (`base_dir`) even
under `instance_eval`. Python closures do the same, so the `base_dir` reference needs no special
handling.

### 5.2 `ensure logger&.close` is an `UnboundLocalError` waiting to happen

```ruby
def self.run(...)
  ...
  logger = Logger.new(...)
  ...
ensure
  logger&.close
end
```

Ruby defines a local from **parse** time, so if an exception fires before the assignment, `logger`
is `nil` and `&.close` is a no-op. **Python raises `UnboundLocalError` in the `finally` block** —
masking the original exception with a confusing one. Initialize before the `try`:

```python
logger = None
try:
    ...
    logger = Logger(...)
    ...
    return agent.run()
finally:
    if logger is not None:
        logger.close()
```

**This is the most dangerous line in the step.** It only fires on the error path — a bad API key,
an unknown backend — so a happy-path test suite will never see it. Test it explicitly.

### 5.3 Symbols → strings for the backend selector

`backend ||= task_class.provider(task_settings).to_sym`, then `case backend when :anthropic`.
Python uses strings throughout (step 01's decision), so `provider(...)` already returns
`"anthropic"` and the `to_sym` disappears. The `ArgumentError` message interpolates
`backend.inspect` — `:anthropic` in Ruby, so the Python message will read `'anthropic'` rather
than `:anthropic`. Accepted divergence; assert the Python text in a test rather than chasing
parity.

### 5.4 `Logger#subscribe` and lazy initialization

```ruby
def subscribe(&block)
  @subscribers ||= []
  @subscribers << block
end
```

`@subscribers` is nil until first use, and `_write_log` guards with `@subscribers&.each`. Mirror
with `self._subscribers = None` in `__init__` and the same lazy create — **not** an eager `[]`.
The distinction is observable: `_write_log` must not iterate when nothing has subscribed, and the
attribute's absence-vs-empty state is what Ruby's `&.` is testing.

Subscribers are called with the event **before** the `session_id`/`at` envelope is merged in —
check the Ruby line order and match it exactly.

### 5.5 Keyword-only, with defaults, and one required

`def self.run(task:, system: nil, ..., &block)` — `task:` required, the rest defaulted. Python:
`def run(*, task, system=None, ..., block=None)`. The `*` matters: Ruby's keyword arguments cannot
be passed positionally, and neither should Python's.

### 5.6 The example header cannot be byte-identical

Every step so far has had a byte-identical header block. Step 07's names the API it demonstrates:

```
Ruby:   === BOUKENSHA Step 7: The Boukensha.run DSL ===
Python: === BOUKENSHA Step 7: The boukensha.run DSL ===
```

`Boukensha.run` does not exist in Python and `boukensha.run` does not exist in Ruby. Copying
Ruby's string verbatim would make the Python example advertise a constant it does not have.
**Accepted divergence** — one character, and the only line of step 07's stdout that differs. §7.3
compares from line 2 onward.

### 5.7 `ollama_host` default is a literal, not from config

`ollama_host: "http://localhost:11434"` is a plain default in the signature, while every other
default resolves from config at call time. Mirror the asymmetry — do not "improve" it by routing
it through `Config`.

---

## 6. Implementation steps

1. **Verify the Ruby baseline** — `./week1_baseline/bin/ruby/check-paths`, then run step 07 and
   keep the output. (§9 is already applied.)
2. **Copy forward** step 06 into `07_the_run_dsl/`, repointing docstrings at `ruby/07_the_run_dsl`.
   Verify `prompts/system.md` still matches.
3. **`boukensha/errors.py`** — re-add `LoopError`.
4. **`boukensha/config.py`** — restore the four `mud_*` readers; restore their tests in
   `tests/test_config.py` from the step-05 tree.
5. **`boukensha/logger.py`** — `turn`, `subscribe`, and the `_write_log` fan-out (§5.4).
6. **`boukensha/run_dsl.py`** — the `RunDSL` class; `tool` as a decorator delegating to `Registry`.
7. **`boukensha/__init__.py`** — `run()`. Follow the Ruby's order of operations exactly, with
   §5.2's `logger = None` guard and §5.1's `block(dsl)` call.
8. **`examples/example.py`** — the DSL in use, with a module-level `register(dsl)` function.
9. **Launcher** — `week1_baseline/bin/python/07_the_run_dsl`.
10. **Tests** — §7.
11. **READMEs** — step README, plus a row in `week1_baseline/python/README.md`.

---

## 7. Verification

### 7.1 Offline suite

*`RunDSL`* (`test_run_dsl.py`)
- `tool` registers on the wrapped registry and returns the undecorated function
- the registered tool is callable through `Registry.dispatch`
- `parameters` defaults to `{}`
- the DSL exposes **only** `tool` — assert the public surface, since containment is its purpose

*`run()`* (`test_run.py`) — with a stubbed `Client` so nothing hits the network
- defaults resolve from settings: provider, model, system prompt, `max_iterations`,
  `max_output_tokens`
- each keyword overrides its default: `system`, `model`, `backend`, `api_key`, `log`,
  `max_output_tokens`
- each of the five backend names builds the right backend class
- an unknown backend raises `ValueError` with the documented message
- `api_key` falls back to the right env var per backend, and `ollama` needs none
- the block is called with a `RunDSL`, and tools it registers reach the agent
- **omitting the block is legal** — `if block` in Ruby; no tools registered, no error
- the user message is appended **once**, after tools are registered
- the `session_start` snapshot carries task, `max_iterations`, `max_output_tokens`, model, provider
- **`logger.close()` is called on the happy path**
- **`logger.close()` is called when the agent raises**, and the original exception propagates
  unchanged (§5.2)
- **an exception raised *before* the logger exists propagates as itself** — not as
  `UnboundLocalError`. This is the §5.2 regression detector; it must exist.

*`Logger`* — extend `test_logger.py`
- `turn(n=)` writes `{"phase": "turn", "n": n}`
- `subscribe` fires for every subsequent event, in order
- multiple subscribers all fire
- no subscribers means `_write_log` still works (the lazy-nil case, §5.4)
- a subscriber sees the event **without** the `session_id`/`at` envelope, matching Ruby's line order

*`Config`* — restore the four `mud_*` tests deleted during the step-06 port, including the
`port: 0` and `host: ""` cases that pin `||` semantics against Python truthiness.

```bash
cd week1_baseline/python && ./run-tests && uv run ruff check .
```

### 7.2 Payload parity (offline, free)

Unchanged in principle, but **the hook moved**: the example no longer builds a `PromptBuilder`, so
there is nothing to dump from the example. Dump from inside `run()` instead — stub the client to
capture `builder.to_api_payload()` on its first call and exit. Compare byte-for-byte with the
Ruby equivalent.

### 7.3 Live run (both trees)

Step 07's console output is the **smallest yet** — a header, the config line, and the final
response. The header block should be byte-identical:

```bash
diff <(sed -n '1,4p' /tmp/rb07.txt) <(sed -n '1,4p' /tmp/py07.txt)
```

Then compare the session logs structurally, as in step 06 — same phase sequence, same key
vocabulary — and additionally check the `session_start` snapshot has the same keys in both trees.

---

## 8. Known drift in the Ruby step-07 reference

**Two features are now yo-yoing across steps.** Both must be mirrored in sequence, not
short-circuited, or the trees stop being diffable step by step:

| | step 05 | step 06 | step 07 |
|---|---|---|---|
| `LoopError` | added, unused | **removed** | **re-added**, still unused |
| `mud_*` config readers | present, unused | **removed** | **restored**, still unused |

Neither has ever had a caller.

- **`Logger#turn` has no caller.** `agent.rb` is byte-identical to step 06's, so nothing emits a
  `"turn"` phase. Ported for parity.
- **`Logger#subscribe` has no caller.** A pub/sub hook with no subscribers anywhere in the tree.
- **`run`'s doc comment is wrong about two defaults.** It says `system:` "Defaults to
  config.system_prompt" and `model:` "Defaults to config.model"; the code reads
  `Tasks::Player.system_prompt(...)` and `Tasks::Player.model(...)`. There is no
  `Config#system_prompt` or `Config#model`. Port the **code**; do not port the comment's claim.
- **`context.rb` lost its trailing newline** and gained misaligned assignment padding. Whitespace
  only.
- **`Config#load_env` was reformatted** from a trailing `if` to a block `if`. No behaviour change.
- **The `mud` block in `settings.yaml` carries a password** (`helloworld`) that nothing reads —
  `mud_password` is restored this step but still has no caller.

---

## 9. Ruby-side changes required before porting

**Already applied, 2026-08-03.** The `check-paths` guard added by
[`../ruby_runnability.md`](../ruby_runnability.md) caught all three on its first real use — the
seventh consecutive occurrence of this regression:

```
FAIL 07_the_run_dsl  BOUKENSHA_DIR -> week1_baseline/.boukensha (does not exist)
FAIL 07_the_run_dsl  PROMPTS_DIR   -> week1_baseline/ruby/prompts (does not exist)
FAIL 07_the_run_dsl  launcher missing or not executable: bin/ruby/07_the_run_dsl
```

Fixed: `examples/example.rb:1` three `..` → four; `lib/boukensha/config.rb:13` three → two;
`bin/ruby/07_the_run_dsl` created at mode 755. Guard now green, and step 07 runs end to end.

**The guard worked exactly as intended** — it turned a silent, deferred, misleading failure into
three named lines before a single API call was made.

---

## 10. Notes

- §5.1 is the first place in seven steps where the Python tree **cannot** mirror the Ruby. Put the
  reasoning in the module docstring, not just this plan — a future reader will otherwise assume
  the divergence was carelessness.
- §5.2 is the highest-risk line: wrong, it converts any startup failure into a misleading
  `UnboundLocalError`, and only on the error path.
- `run()` is the first function to construct almost the entire object graph. Its test file is
  effectively an integration suite; a stub `Client` is the only seam needed, because everything
  else is already independently tested.
- With `run()` in place, the example stops being a wiring tutorial. That is the step's point —
  and it means the example is no longer where a reader learns how the pieces connect. The step
  README should carry a "what `run` does for you" section that the example used to demonstrate.
