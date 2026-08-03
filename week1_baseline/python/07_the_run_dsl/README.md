# 07 · The Run DSL (Python)

Python port of `week1_baseline/ruby/07_the_run_dsl`.

> Requires the shared environment. If you haven't run `uv sync` in `week1_baseline/python`, do
> that first — see [`../README.md`](../README.md).

Steps 00–06 built primitives and made the example wire them together by hand. Step 07 adds the
front door.

**Before** (step 06's example, ~80 lines): build a `Config`, read task settings, resolve the
system prompt, build a `Context`, a `Registry`, branch five ways on provider to build a backend,
then a `PromptBuilder`, a `Client`, a `Logger`, an `Agent`, register tools, append the user
message, call `run`.

**After:**

```python
def register(dsl):
    @dsl.tool(
        "read_file",
        description="Read a file from disk",
        parameters={"path": {"type": "string", "description": "File path"}},
    )
    def read_file(*, path):
        return Path(path).read_text()


result = boukensha.run(task="Read the README and summarise it", block=register)
```

Everything else defaults from `settings.yaml` and `.env`, and every default is overridable:
`system`, `model`, `backend`, `api_key`, `ollama_host`, `log`, `max_output_tokens`.

## ⚠️ The one place the two trees diverge

Seven steps in, this is the first thing that **cannot** be mirrored. Ruby writes:

```ruby
RunDSL.new(registry).instance_eval(&block)
```

`instance_eval` rebinds `self` inside the caller's block, so a bare `tool "..."` resolves to
`RunDSL#tool`. **Python has no supported equivalent** — a function's name resolution is fixed at
compile time. So the block receives the DSL as an argument instead:

| Ruby | Python |
|---|---|
| `run(task: "...") do` <br> `  tool "read_file", ... do \|path:\|` | `def register(dsl):` <br> `    @dsl.tool("read_file", ...)` <br> `    def read_file(*, path):` <br><br> `run(task="...", block=register)` |

Rejected alternatives, with reasons, are in the step plan §5.1 — the short version is that
rewriting `block.__globals__`, `exec`-ing against a namespace, or walking frames are all fragile,
break tooling, and are not thread-safe.

The containment Ruby gets from rebinding `self`, Python gets from the block only ever receiving
the `RunDSL` — which exposes `tool` and nothing else. A test asserts that surface.

**One thing ports for free:** Ruby's block closes over enclosing locals (`base_dir`) even under
`instance_eval`, and Python closures do the same.

## What `run` does for you

In order:

1. `config()` — loads `.env` into the environment, memoized
2. Resolves `system`, `model`, `backend` from the `player` task's settings
3. Resolves `api_key` from the matching env var (`ollama` needs none)
4. Builds a `Context` and `Registry`, then calls your block with a `RunDSL`
5. Builds the backend, `PromptBuilder`, `Client`
6. Builds a `Logger` with a snapshot of the effective config
7. Builds the `Agent`, appends your task as the user message, runs it
8. Closes the logger — **on every path, including failure**

Step 07's `session_start` line now records the whole effective configuration:

```json
{"phase":"session_start","task":"player","max_iterations":25,"max_output_tokens":1024,
 "model":"claude-sonnet-4-6","provider":"anthropic","session_id":"...","at":"..."}
```

## Code map

| File | Purpose | Ruby original |
|------|---------|---------------|
| `boukensha/run_dsl.py` | `RunDSL` — exposes only `tool` | `lib/boukensha/run_dsl.rb` |
| `boukensha/__init__.py` | `run()` — the whole wiring | `lib/boukensha.rb` → `self.run` |
| `boukensha/logger.py` | `+ turn()`, `+ subscribe()` | `lib/boukensha/logger.rb` |
| `boukensha/errors.py` | `+ LoopError` (again) | `lib/boukensha/errors.rb` |
| `boukensha/config.py` | `+ mud_*` readers (again) | `lib/boukensha/config.rb` |
| `tests/test_run.py` | 24 tests — effectively an integration suite | *(none)* |
| `tests/test_run_dsl.py` | 6 tests | *(none)* |
| everything else | carried forward from step 06, **`agent.py` included** | |

## Differences from the Ruby original

Earlier steps' tables still apply. New here:

| Ruby | Python | Why |
|------|--------|-----|
| `instance_eval(&block)` | `block(RunDSL(registry))` | See above. The only structural divergence in seven steps. |
| `ensure logger&.close` | `logger = None` before `try`, `finally: if logger is not None` | **The most dangerous line in the step.** Ruby defines locals from parse time, so `&.close` is a no-op when the logger was never built. Python raises `UnboundLocalError` in `finally` and **masks the original error** — and only on the failure path, so a happy-path suite never sees it. Pinned by a test. |
| `provider(...).to_sym`, `case :anthropic` | plain strings | The Python tree has used strings for roles and providers since step 01. |
| `backend.inspect` → `:anthropic` | `{backend!r}` → `'anthropic'` | The `ArgumentError`/`ValueError` message reads differently. Asserted as Python text rather than chased for parity. |
| `@subscribers ||= []` + `&.each` | `self._subscribers = None`, lazily created | Not an eager `[]` — absence-vs-empty is exactly what Ruby's safe-navigation is testing. |
| `=== ... The Boukensha.run DSL ===` | `=== ... The boukensha.run DSL ===` | The header names the API it demonstrates, and that name differs by language. Copying Ruby's string would make the Python example advertise a constant it doesn't have. |

## Known defects, carried over from Ruby

**Two features are now yo-yoing across steps**, and neither has ever had a caller:

| | step 05 | step 06 | step 07 |
|---|---|---|---|
| `LoopError` | added, unused | removed | **re-added**, still unused |
| `mud_*` config readers | present, unused | removed | **restored**, still unused |

Each state change is mirrored in sequence so the trees stay diffable step by step.

- **`Logger.turn` has no caller.** `agent.py` is byte-identical to step 06's, so nothing emits a
  `"turn"` phase.
- **`Logger.subscribe` has no caller.** A pub/sub hook with no subscribers anywhere.
- **Ruby's `run` doc comment is wrong about two defaults.** It claims `system:` and `model:`
  default to `config.system_prompt` / `config.model`; there are no such methods. Both resolve
  through `Tasks::Player`. The code is ported; the comment's claim is not.
- **`settings.yaml` carries a `mud` password** that nothing reads.

## Run

```bash
./week1_baseline/bin/python/07_the_run_dsl
```

> **Makes several billed API calls.** Needs `ANTHROPIC_API_KEY` in `.boukensha/.env`. Session
> logs land in gitignored `.boukensha/sessions/`.

Parity is checked three ways — the header from line 2 onward (line 1 differs by design, above),
the built payload byte-for-byte, and the session log structurally (phase sequence, key
vocabulary, and `session_start` snapshot keys). Recipes in the step plan §7.2–7.3.

## Test

```bash
cd week1_baseline/python
uv run pytest 07_the_run_dsl
```

365 tests, all offline. `test_run.py` is effectively an integration suite — `run()` builds almost
the entire object graph, and a stub `Client` is the only seam needed because everything else is
independently tested.
