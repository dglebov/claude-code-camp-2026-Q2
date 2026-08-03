# 06 · The Logger (Python)

Python port of `week1_baseline/ruby/06_the_logger`.

> Requires the shared environment. If you haven't run `uv sync` in `week1_baseline/python`, do
> that first — see [`../README.md`](../README.md).

Step 05's agent narrated to stdout. Step 06 replaces that entirely with structured events written
to `.boukensha/sessions/<session-id>.jsonl`, one JSON object per line.

```
Agent.run ──► Logger ──► .boukensha/sessions/20260803T175732Z-282e6720.jsonl
                          {"phase":"session_start", ...}
                          {"phase":"iteration","n":1,"max":25, ...}
                          {"phase":"prompt","message_count":1,"tool_count":2, ...}
                          {"phase":"response","text":"...","cost_usd":0.003087, ...}
                          {"phase":"tool_call","name":"read_file", ...}
                          {"phase":"tool_result","name":"read_file","ok":true, ...}
                          {"phase":"turn_end","reason":"completed","iterations":2, ...}
```

**The console goes quiet.** `Agent` no longer prints anything — the example shows its header block
and the final response, and nothing in between.

## `Logger`

| Event | Written when |
|---|---|
| `session_start` | construction; merges any `snapshot=` kwargs |
| `iteration` | each counted loop pass — `n`, `max` |
| `prompt` | before each call — message/tool counts, serialized messages, tool **names** |
| `response` | after each reply — text, usage, cost, task, provider, model |
| `tool_call` | before dispatch — name, args |
| `tool_result` | after dispatch — result, `ok`, `error` |
| `limit_reached` | the ceiling trips, immediately before the wind-down |
| `turn_end` | exactly once per turn, on every exit path |
| `raw` | **only when `boukensha.debug()` has been called** — the full provider response |
| *(close)* | `close()` releases the handle; the example never calls it |

Every line carries `session_id` and an ISO-8601 `at`.

Constructor: `Logger(session_id=None, dir=None, log=None, snapshot=None)`. `session_id` defaults to
`%Y%m%dT%H%M%SZ-<8 hex>`; `dir` defaults to `<config.dir>/sessions`; `log` overrides the full path.

### Usage and cost

`response` events normalize token usage across four provider vocabularies and price it through the
backend's existing `estimate_cost`:

| Provider | Input key | Output key |
|---|---|---|
| Anthropic | `input_tokens` | `output_tokens` |
| OpenAI | `prompt_tokens` | `completion_tokens` |
| Gemini | `promptTokenCount` | `candidatesTokenCount` |
| Ollama | `prompt_eval_count` | `eval_count` |

## Module-level state

New in this step, mirroring Ruby's `@config` / `@debug` / `@quiet` module variables:

```python
import boukensha

boukensha.config()      # memoized Config
boukensha.debug()       # make Logger.raw write the full response
boukensha.is_debug()
boukensha.quiet(); boukensha.loud(); boukensha.is_quiet()
```

`debug?`/`quiet?` become `is_debug()`/`is_quiet()` — `?` is not a legal Python identifier
character, and the bare names are taken by the setters.

This is a departure from five steps of dependency injection. `Agent` still takes every
collaborator by constructor argument; only `Logger` reads the globals.

## Code map

| File | Purpose | Ruby original |
|------|---------|---------------|
| `boukensha/logger.py` | The whole step | `lib/boukensha/logger.rb` |
| `boukensha/__init__.py` | Module state + accessors, `Logger` export | `lib/boukensha.rb` |
| `boukensha/agent.py` | Logging replaces printing; tool errors caught | `lib/boukensha/agent.rb` |
| `boukensha/prompt_builder.py` | `+ backend` property | `lib/boukensha/prompt_builder.rb` |
| `boukensha/errors.py` | **`LoopError` removed** | `lib/boukensha/errors.rb` |
| `boukensha/config.py` | **`mud_*` readers removed** | `lib/boukensha/config.rb` |
| `tests/test_logger.py` | 33 tests | *(none — Ruby ships no specs)* |
| `tests/test_agent.py` | **rewritten** for the logger | *(none)* |

## Differences from the Ruby original

Earlier steps' tables still apply. New here:

| Ruby | Python | Why |
|------|--------|-----|
| `logger: Logger.new` default arg | `logger=None` + `logger if logger is not None else Logger()` | **The one that matters.** Python evaluates defaults **once, at import**, so a literal port would give every Agent the *same* logger and would open a log file as a side effect of importing the module. Pinned by a test asserting two Agents get different instances. |
| `Boukensha.debug?` at call time | deferred `from . import is_debug` inside the method | `boukensha/__init__.py` imports `logger.py`, so a module-level import back would be circular. Ruby has no equivalent problem. The deferred import mirrors Ruby's call-time resolution. |
| `Hash#compact` | `{k: v for k, v in … if v is not None}` | `compact` drops nil only. A truthiness filter would drop a `0` token count and the `0.0` cost every local Ollama model reports. |
| `rescue ArgumentError, TypeError` on the method | one `try` around the whole loop | Ruby's rescue is method-scoped, so a bad value aborts the **entire** lookup instead of falling through to the next key. A per-key `try` would be more useful and would diverge. |
| `SecureRandom.hex(4)` | `secrets.token_hex(4)` | 4 bytes, 8 hex characters. Not `uuid4` — the id format appears in filenames. |
| `Time.now.iso8601` | `datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z")` | Python would otherwise emit microseconds and `+00:00`. Trimmed so both logs read the same. |
| `backend.class.name.split("::").last` | `type(backend).__name__` | Already the bare name in Python; only the snake_case regex is needed. |
| `rescue StandardError` around tool dispatch | `except Exception` (`# noqa: BLE001`) | Ruby's `StandardError` **is** the blind catch. Ruff objects; the suppression is deliberate. |

## Known defects, carried over from Ruby

- **`quiet!`/`loud!`/`quiet?` are declared and never consumed.** Nothing reads the flag.
- **`LoopError` was added unused in step 05 and removed in step 06.** Both moves mirrored in
  sequence so the trees stay diffable at each step.
- **The four `mud_*` config readers are removed.** Nothing referenced them; reads as a deliberate
  removal, not a regression.
- **`Logger.close` is never called** by the example or by `Agent`. Writes are flushed individually
  so nothing is lost, but a long-lived process would leak the handle.
- **`cost_usd` is absent for Ollama Cloud** (prices per plan, `None`) and **present-but-zero** for
  local Ollama.

## Run

```bash
./week1_baseline/bin/python/06_the_logger
```

> **Makes several billed API calls** — one per iteration. Needs `ANTHROPIC_API_KEY` in
> `.boukensha/.env`. Session logs land in `.boukensha/sessions/` and are gitignored: each line
> carries the full conversation, including the contents of any file the tools read.

Parity against Ruby is checked three ways — none of them a plain `diff` of the whole run, since
the model's prose varies:

1. **The header block is byte-identical.** `diff <(sed -n '1,8p' rb.txt) <(sed -n '1,8p' py.txt)`
2. **The built payload is byte-identical** — see the step plan §7.2 for the dump recipe.
3. **The logs match structurally:** same phase sequence and same key vocabulary.
   ```bash
   diff <(jq -r '.phase' rb.jsonl)              <(jq -r '.phase' py.jsonl)
   diff <(jq -s 'map(keys)|flatten|unique' rb.jsonl) <(jq -s 'map(keys)|flatten|unique' py.jsonl)
   ```

## Test

```bash
cd week1_baseline/python
uv run pytest 06_the_logger
```

322 tests, all offline: 33 for `Logger`, 7 for the module state, a rewritten `test_agent.py`, and
the rest carried forward.
