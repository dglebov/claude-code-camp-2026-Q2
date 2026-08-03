# Python Port Plan — Step 06 · The Logger

Port `week1_baseline/ruby/06_the_logger` to `week1_baseline/python/06_the_logger`.

**Scope:** week1 only, step 06 only. Builds on the completed step-05 port; reuses the shared
environment at `week1_baseline/python/` (no new venv, no new dependencies).

**Prerequisites:** the Ruby reference does not run and has no launcher. See
[`../ruby_runnability.md`](../ruby_runnability.md) §3 — that plan supersedes what would otherwise
be this document's §9.

Comparable in size to step 05, but the interesting work is different: one new class of moderate
size, and a **behavioural change to the console** that makes output parity *easier* than it was in
step 05.

---

## 1. Decisions (settled — do not re-litigate)

| Decision | Choice |
|----------|--------|
| Broken Ruby reference | **Fix Ruby first** via `ruby_runnability.md` §3 — two path lines plus the missing launcher — then port. |
| Module-level state (`Boukensha.config`, `.debug?`, `.quiet?`) | **Mirror it.** Module-level mutable state on the `boukensha` package, matching Ruby's `@config`/`@debug`/`@quiet` module ivars. It is a design shift worth flagging (§8) but the port's job is to mirror, not to improve. |
| `quiet!`/`loud!`/`quiet?` | **Mirror, flag.** Declared and never consumed — the same dead-code treatment as `LoopError` in 05. |
| Timestamps and session ids | Non-deterministic by nature. Tests inject a fixed `session_id` and freeze the clock; **the JSONL is never compared byte-for-byte across trees.** |
| Log destination in tests | `tmp_path`, always. No test may write into the real `.boukensha/sessions/`. |
| Structure | Mirror Ruby 1:1, as in steps 00–05. |
| Environment | Shared `.venv`. `json`, `uuid`, `datetime`, `pathlib` are all stdlib — `secrets.token_hex` replaces `SecureRandom.hex`. |

---

## 2. Reference files — what to port

Source of truth is `week1_baseline/ruby/06_the_logger/`. Delta established with a **whole-tree**
`diff -rq`, not `*.rb` only.

### New in this step

| Read this | Purpose | Becomes |
|---|---|---|
| `lib/boukensha/logger.rb` | JSONL session logger — 10 event kinds, usage/cost extraction | `boukensha/logger.py` |
| `examples/example.rb` | Same shape as step 05, plus a `Logger` wired into the agent | `examples/example.py` |
| `README.md` | Step README | `06_the_logger/README.md` (adapted) |

### Changed vs step 05

| File | Delta |
|---|---|
| `boukensha/__init__.py` | **Module-level state and accessors** — `config()`, `quiet()`, `loud()`, `is_quiet()`, `debug()`, `is_debug()`. Plus `Logger` in the exports. Ruby memoizes `Config.new` in `self.config`; Python does the same with a module global. |
| `boukensha/agent.py` | **All `print` calls replaced by logger calls.** New `logger=` constructor arg defaulting to a fresh `Logger`. `handle_tool_calls` gains a `response` parameter, wraps `registry.dispatch` in a try/except that turns a raised tool into a logged `ok=False` result instead of propagating, and logs the assistant's reasoning text. New private `log_response` and `normalized_usage`. |
| `boukensha/prompt_builder.py` | Add a `backend` property — `agent.log_response` reads `builder.backend`. |
| `boukensha/errors.py` | **Remove `LoopError`.** Added unused in step 05, deleted here. |
| `boukensha/config.py` | **Remove the four `mud_*` readers.** Deliberate removal in Ruby, not a regression (§8). `PROMPTS_DIR` stays at `"../../prompts"` — do not copy Ruby's regressed value. |

### Carried forward from step 05 — unchanged

`boukensha/{client,context,env_file,message,registry,tool}.py`, all of `boukensha/backends/`,
`boukensha/tasks/`, `prompts/system.md`, `conftest.py`, and the existing `tests/test_*.py` except
the four noted in §7.

`context.rb` and `config.rb` also differ by whitespace-only realignment — no Python change.

---

## 3. What step 06 actually adds

Step 05's agent narrated to stdout. Step 06 replaces that entirely with structured events written
to `.boukensha/sessions/<session-id>.jsonl`, one JSON object per line.

```
Agent.run ──► Logger ──► .boukensha/sessions/20260803T183412Z-a1b2c3d4.jsonl
                          {"phase":"session_start", ...}
                          {"phase":"iteration","n":1,"max":25, ...}
                          {"phase":"prompt","message_count":1,"tool_count":2, ...}
                          {"phase":"tool_call","name":"read_file", ...}
                          {"phase":"tool_result","name":"read_file","ok":true, ...}
                          {"phase":"response","text":"...","cost_usd":0.0021, ...}
                          {"phase":"turn_end","reason":"completed","iterations":2, ...}
```

**Ten event kinds:** `session_start`, `iteration`, `limit_reached`, `turn_end`, `prompt`,
`tool_call`, `tool_result`, `response`, `raw` (debug-only), plus `close`. Every line is stamped
with `session_id` and an ISO-8601 `at`.

Three things carry the step:

**1. The console goes quiet.** `agent.rb` no longer calls `puts` at all. The example prints its
header block and the final response, and nothing in between. **This makes output parity easier
than step 05** — the only non-deterministic part of stdout is the model's prose.

**2. Tool failures stop being fatal.** `registry.dispatch` is now wrapped: a raised tool becomes
`"ERROR: <Class>: <message>"` as the tool result, logged with `ok=false`, and the loop continues.
Previously the exception propagated out of `run`.

**3. Usage and cost normalization.** `response` events carry `input_tokens`, `output_tokens` and
`cost_usd`, extracted across four provider vocabularies (`input_tokens`/`prompt_tokens`/
`promptTokenCount`/`prompt_eval_count` and their output counterparts) and priced via the backend's
existing `estimate_cost`.

---

## 4. Target layout

```
week1_baseline/python/06_the_logger/
  boukensha/
    __init__.py            # + module state, config(), debug(), quiet(), Logger export
    logger.py              # NEW — the whole step
    agent.py               # print -> logger; tool errors caught; log_response/normalized_usage
    prompt_builder.py      # + backend property
    errors.py              # - LoopError
    config.py              # - mud_* readers
    …                      # rest copy-forward
  examples/example.py      # + Logger wired in
  tests/
    test_logger.py         # NEW
    test_agent.py          # rewritten — asserts logger calls, not stdout
    …
```

Plus `week1_baseline/bin/python/06_the_logger`.

---

## 5. Ruby → Python semantic gaps new to this step

### 5.1 Module-level state

Ruby's `module Boukensha; @config = nil; def self.config = @config ||= Config.new; end` becomes a
module global plus functions in `boukensha/__init__.py`:

```python
_config = None
_quiet = False
_debug = False


def config():
    global _config
    if _config is None:
        _config = Config()
    return _config
```

Ruby's `self.config` is a *method*; Python's is a *function* — call sites read `config()` either
way, so the difference is invisible. **`debug?` → `is_debug()`**, since `?` is not a legal Python
identifier character and `debug` is already taken by the setter. Same for `quiet?` → `is_quiet()`.

**Tests must reset this state.** A module global memoized across tests leaks between them; add an
autouse fixture that clears `_config`/`_quiet`/`_debug`.

### 5.2 `SecureRandom.hex(4)` → `secrets.token_hex(4)`

Both yield 8 hex characters from 4 random bytes. Do **not** reach for `uuid4()` — the id format is
`%Y%m%dT%H%M%SZ-<8 hex>` and appears in filenames.

### 5.3 `Time.now.iso8601` → `datetime.now(UTC).isoformat()`

Ruby's `Time#iso8601` renders `2026-08-03T18:34:12Z` (local offset, or `Z` for UTC). Python's
`datetime.now(UTC).isoformat()` renders `2026-08-03T18:34:12.123456+00:00` — **microseconds and
`+00:00` instead of `Z`.** Not identical. Since the JSONL is never compared across trees (§1) this
is cosmetic, but match it anyway with `.replace(microsecond=0).isoformat().replace("+00:00", "Z")`
so the two logs read the same to a human.

Note `generate_session_id` uses `Time.now.utc.strftime` (explicitly UTC) while `write_log` uses
`Time.now.iso8601` (local). Mirror the asymmetry.

### 5.4 `File.open(path, "a")` and the unclosed handle

Ruby opens an append handle in the constructor and holds it for the object's life. `close` exists
but **the example never calls it** — the file is flushed after every write, so nothing is lost, and
the handle is released at process exit. Mirror it: open in `__init__`, `flush()` after each write.
Do **not** convert this into a context manager; that would change the call shape the example uses.

### 5.5 `backend&.respond_to?(:usage_unit) ? backend.usage_unit : nil`

Ruby's safe-navigation binds tighter than the ternary, so this reads
`(backend && backend.respond_to?(...)) ? ... : nil`. Python:
`backend.usage_unit if backend is not None and hasattr(backend, "usage_unit") else None`.

### 5.6 `metadata.compact` → drop `None` values

`Hash#compact` removes nil values only. `{k: v for k, v in metadata.items() if v is not None}` —
note it must be `is not None`, not truthiness, or a legitimate `0` token count or `0.0` cost is
dropped. Ollama models price at `0.0`, so this is a live case, not a hypothetical.

### 5.7 `first_integer` and its rescue

```ruby
return Integer(value) unless value.nil?
...
rescue ArgumentError, TypeError
  nil
```

The `rescue` is on the whole method, so a bad value anywhere returns `nil` for the *whole lookup*
rather than falling through to the next key. Mirror that: wrap the entire loop in
`try/except (ValueError, TypeError): return None`. A per-key `try` would be more useful and would
diverge.

### 5.8 `backend.class.name.split("::").last.gsub(...)` → snake_case

Ruby derives `ollama_cloud` from `Boukensha::Backends::OllamaCloud` via
`gsub(/([a-z\d])([A-Z])/, '\1_\2').downcase`. Python: `type(backend).__name__` is already just
`OllamaCloud`, so only the regex is needed —
`re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name).lower()`. Verify `OpenAI` → `open_ai` in both (it
does — there is no lowercase/digit before the `A`... check this in a test, it is the one name where
the regex is surprising).

### 5.9 `msg.role` in `serialize_message`

Ruby stores roles as symbols and JSON-encodes them as strings. Python's are already strings
(step 01). `{"role": msg.role, "content": msg.content}` needs no conversion — but note the message
`content` may be a **list of blocks** for assistant turns since step 05, and `json.dumps` handles
that fine.

### 5.10 Default argument evaluated once

`def initialize(..., logger: Logger.new, ...)` constructs a **fresh** logger per Agent in Ruby.
Python's `def __init__(self, ..., logger=Logger())` would construct **one** at import time, shared
by every Agent — and it would open a log file as a side effect of importing the module. Use
`logger=None` and `self._logger = logger if logger is not None else Logger()`.

**This is the most dangerous line in the step.** A literal transcription is silently wrong, creates
a stray session file on import, and every test would share one logger.

---

## 6. Implementation steps

1. **Fix and verify the Ruby reference** — `ruby_runnability.md` §3, then capture a baseline run.
2. **Copy forward** step 05 into `06_the_logger/`, repointing docstrings at `ruby/06_the_logger`.
   Verify `prompts/system.md` still matches.
3. **`boukensha/errors.py`** — remove `LoopError`.
4. **`boukensha/config.py`** — remove the four `mud_*` readers.
5. **`boukensha/prompt_builder.py`** — add the `backend` property.
6. **`boukensha/logger.py`** — the class. Ten event methods, then the private helpers.
7. **`boukensha/__init__.py`** — module state + accessors, `Logger` export, `LoopError` removed.
8. **`boukensha/agent.py`** — swap prints for logger calls, `logger=None` (§5.10), the tool
   try/except, `log_response`, `normalized_usage`.
9. **`examples/example.py`** — construct a `Logger`, pass it to `Agent`, update the header string.
10. **Launcher** — `week1_baseline/bin/python/06_the_logger`.
11. **Tests** — §7.
12. **READMEs** — step README, plus a row in `week1_baseline/python/README.md`.

---

## 7. Verification

### 7.1 Offline suite

*`Logger`* (`test_logger.py`) — all writing to `tmp_path`
- the constructor creates the directory, opens the file, and writes a `session_start` line
- `snapshot=` kwargs are merged into that first line
- an explicit `session_id` is used verbatim; a generated one matches `\d{8}T\d{6}Z-[0-9a-f]{8}`
- `log=` overrides the path; `dir=` overrides only the directory
- every line is valid JSON and carries `session_id` and `at`
- one method per event kind writes the documented shape
- `prompt` records `message_count`/`tool_count` and the **tool names**, not the tool objects
- `raw` writes **nothing** unless `is_debug()`; writes when it is
- `response` extracts usage across all four vocabularies (Anthropic, OpenAI, Gemini, Ollama)
- `response` computes `cost_usd` from the backend, and **keeps a `0.0` cost** rather than
  dropping it (§5.6) — the Ollama case
- `response` omits keys whose value is `None`
- a non-numeric usage value yields `None` for the whole lookup (§5.7)
- `provider_name` renders `OllamaCloud` → `ollama_cloud` and `OpenAI` → whatever the regex gives
  (§5.8) — assert the actual value, in both trees
- `close` closes the handle; writing after close raises

*`Agent`* (`test_agent.py` — **rewritten**, not extended)
- every step-05 behaviour still holds, but asserted against a **spy logger** rather than capsys
- `iteration`, `prompt`, `tool_call`, `tool_result`, `response`, `turn_end` fire in the right
  order with the right arguments
- **a tool that raises is caught**: the result is `"ERROR: ValueError: boom"`, it is logged with
  `ok=False` and the error message, and the loop continues rather than propagating
- `limit_reached` fires exactly once when the ceiling trips, before the wind-down
- `turn_end` fires exactly once on every exit path: completion, wind-down, and `ApiError`
- assistant reasoning is logged; when there is none, the placeholder
  `"(tool use — N call(s))"` is used, with correct pluralisation at N=1 and N=2
- **no logger is constructed at import time** (§5.10): two Agents built without a `logger=`
  argument get **different** Logger instances
- `normalized_usage` picks `usage`, then `usageMetadata`, then the Ollama pair, then `None`

*module state* (`test_module_state.py`)
- `config()` memoizes — two calls return the same object
- `debug()`/`is_debug()` and `quiet()`/`loud()`/`is_quiet()` round-trip
- an autouse fixture resets all three between tests (§5.1)

```bash
cd week1_baseline/python && ./run-tests && uv run ruff check .
```

### 7.2 Payload parity (offline, free)

Unchanged from step 05 §7.2 — dump `builder.to_api_payload()` and the wind-down payload from both
trees and diff. Still the cheapest real parity evidence.

### 7.3 Live run (both trees)

**Easier than step 05.** The agent no longer prints a trace, so stdout is just the header block and
the final prose. The header block should be **byte-identical** between trees:

```bash
./week1_baseline/bin/ruby/06_the_logger   > /tmp/rb06.txt
./week1_baseline/bin/python/06_the_logger > /tmp/py06.txt
diff <(sed -n '1,8p' /tmp/rb06.txt) <(sed -n '1,8p' /tmp/py06.txt)   # header only
```

Then compare the **logs structurally** — not byte-for-byte (§1):

```bash
for f in .boukensha/sessions/*.jsonl; do
  jq -r '.phase' "$f" | uniq -c        # same phase sequence?
  jq -s 'map(keys) | flatten | unique' "$f"   # same key vocabulary?
done
```

Both trees should produce the same phase sequence and the same key set. Values will differ.

---

## 8. Known drift in the Ruby step-06 reference

- **`quiet!`/`loud!`/`quiet?` are declared and never consumed.** Nothing reads `@quiet`. Same dead
  code treatment as step 05's `LoopError` — which this step deletes, having added it one step
  earlier.
- **`LoopError` was added in 05 and removed in 06** without ever being raised. Both moves are
  mirrored, in sequence, so the trees stay diffable at each step.
- **The four `mud_*` config readers are removed.** Nothing references them, and no MUD connection
  code exists yet. Reads as a deliberate removal rather than a regression; do not restore them.
- **`Logger#close` is never called** by the example or by `Agent`. Writes are flushed individually
  so nothing is lost, but a long-lived process would leak the handle.
- **`normalized_usage` handles four vocabularies but `estimate_cost` only prices two of them
  meaningfully** — Ollama is `0.0` and OllamaCloud is `None`. Not a bug, but the `cost_usd` field
  is absent for Ollama Cloud and present-but-zero for local Ollama.
- **Module-level mutable state is a design shift** from five steps of dependency injection.
  `Agent` still takes everything by constructor argument; the new globals are used only by
  `Logger.default_dir` and `Logger.raw`. Worth watching if it spreads.

---

## 9. Ruby-side changes required before porting

**Superseded by [`../ruby_runnability.md`](../ruby_runnability.md).** That plan covers step 06's
two path fixes, the missing launcher, and the guard intended to stop the regression recurring in
step 07. Complete it before starting §6 here.

---

## 10. Notes

- The console going quiet is the step's most user-visible change and the reason §7.3 is simpler
  than step 05's. Do not "helpfully" keep the prints — their removal is the point.
- `test_agent.py` is a **rewrite**, not an extension. Every step-05 assertion that read stdout has
  to be re-expressed against the spy logger. Budget for it; it is the largest single piece of work
  in the step, larger than `logger.py` itself.
- With `Logger` in place, every step-04/05 assertion about cost and usage finally has a consumer —
  `estimate_cost` has existed unused since step 03.
