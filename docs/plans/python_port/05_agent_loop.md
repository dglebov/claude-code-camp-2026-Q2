# Python Port Plan — Step 05 · The Agent Loop

Port `week1_baseline/ruby/05_agent_loop` to `week1_baseline/python/05_agent_loop`.

**Scope:** week1 only, step 05 only. Builds on the completed step-04 port; reuses the shared
environment at `week1_baseline/python/` (no new venv, no new dependencies).

**Prerequisites:** the Ruby reference **does not run**. Two blocking path bugs must be fixed
before there is a baseline to prove parity against — see §9.

Much larger than step 04. One new class, a new method on all five backends, and a new response
contract threaded through the builder and client.

---

## 1. Decisions (settled — do not re-litigate)

| Decision | Choice |
|----------|--------|
| Broken Ruby reference | **Fix Ruby first, then port** (§9), as in steps 00–04. Two bugs, both regressions of bugs already fixed in earlier steps. |
| Normalized response keys | Ruby returns `{ stop_reason:, content: }` — **symbol** keys on the outer hash, **string** keys on the inner blocks. Python uses string keys throughout: `{"stop_reason": ..., "content": [...]}`. Consistent with step 01's symbol→string decision; the inner blocks already match because they come from parsed JSON. |
| `LoopError` | **Mirror it, flag it.** Declared in `errors.rb`, documented in the README, and never raised. Port the class, record in §8. Same treatment as `token_budget` (01) and `to_messages` (03). |
| Agent's stdout tracing | **Mirror.** `puts` → `print()`. The iteration/tool trace is part of the output parity target. |
| Test strategy | **Fake client + scripted responses.** `Agent` takes its client by constructor injection already, so no patching is needed for the loop tests — a stub client returning canned payloads drives every path. Backend `parse_response` tests need no mocking at all. |
| Structure | Mirror Ruby 1:1, as in steps 00–04. |
| Environment | Shared `week1_baseline/python/.venv`. No new dependencies. |

---

## 2. Reference files — what to port

Source of truth is `week1_baseline/ruby/05_agent_loop/`.

Delta established with a **whole-tree** `diff -rq`, not a `*.rb`-only content diff. Step 04's plan
missed a rewritten `prompts/system.md` that way; here `prompts/system.md` is confirmed **unchanged**
from step 04.

### New in this step — the actual work

| Read this | Purpose | Becomes |
|---|---|---|
| `lib/boukensha/agent.rb` | The loop: call → parse → dispatch tools → repeat, with an iteration ceiling and a wind-down call | `boukensha/agent.py` |
| `examples/example.rb` | Smoke test: registers two filesystem tools, asks the model to read and summarise the README, runs the loop | `examples/example.py` |
| `README.md` | Step README | `05_agent_loop/README.md` (adapted) |

### Changed vs step 04

| File | Delta |
|---|---|
| `backends/{anthropic,openai,gemini,ollama,ollama_cloud}.py` | **`parse_response(response)`** on each — normalizes that provider's reply into the common shape. **`to_payload(..., tools=None)`** — when `tools` is passed it *replaces* the serialized tool list, which is how the wind-down call disables tools. Gemini additionally gains a private `assistant_parts`, the inverse of `parse_response`, so an assistant turn carrying tool_use blocks can be re-serialized. |
| `boukensha/prompt_builder.py` | `to_api_payload(max_output_tokens=1024, tools=None)`; new `parse_response(response)` delegator. |
| `boukensha/client.py` | `call(max_output_tokens=1024, tools=None)` — threads `tools` to `to_api_payload`. Nothing else changes; the retry logic is untouched. |
| `boukensha/tasks/base.py` | `DEFAULT_MAX_ITERATIONS = 25`, `DEFAULT_MAX_OUTPUT_TOKENS = 1024`, `max_iterations()`, `max_output_tokens()`, and a private `_integer_setting()`. |
| `boukensha/errors.py` | Add `LoopError` (unused — §8). |
| `boukensha/__init__.py` | Add `Agent` and `LoopError`. |
| `boukensha/config.py` | **No Python change.** Ruby converted four `mud_*` readers to endless method definitions — pure syntax. `PROMPTS_DIR` must stay at `"../../prompts"`; do **not** copy Ruby's regressed value (§9.2). |

### Carried forward from step 04 — unchanged

`boukensha/{context,env_file,message,registry,tool}.py`, `boukensha/tasks/{__init__,player}.py`,
`boukensha/backends/base.py`, `prompts/system.md`, `conftest.py`, and every existing
`tests/test_*.py` except the four noted in §7.

### Context only — do not port

- `week1_baseline/ITERATIONS.md` §5.
- `docs/plans/python_port/0{0,1,2,3,4}_*.md` — §5 of each still applies.

---

## 3. What step 05 actually adds

Step 04 made one call and returned raw JSON. Step 05 turns that into a conversation that runs
itself.

```
Agent.run
  └─ loop:
       client.call            → raw provider JSON
       builder.parse_response → {"stop_reason": ..., "content": [...]}
       stop_reason == "tool_use" ?
          yes → append assistant turn, dispatch each tool, append results, loop
          no  → return the joined text
```

Three ideas carry the step:

**1. A normalized response shape.** Every provider disagrees about replies just as they disagree
about requests. `parse_response` collapses them to one contract:

```python
{"stop_reason": "tool_use" | "end_turn",
 "content": [{"type": "text", "text": ...},
             {"type": "tool_use", "id": ..., "name": ..., "input": {...}}]}
```

Anthropic's is nearly a pass-through. Gemini's is the most work: it walks
`candidates[0].content.parts`, maps `functionCall` → `tool_use`, and **reuses the function name as
the call id** because Gemini assigns none.

**2. Limits are trigger thresholds, not hard caps.** On reaching `max_iterations` the agent does
not raise. It appends a directive telling the model to stop calling tools and summarize, then makes
**one** final call with `tools=[]` and a reduced 400-token budget. That call runs *outside* the
counted loop — it cannot re-trigger the limit and does not increment the counter. If it fails with
`ApiError`, a deterministic fallback sentence is returned instead.

**3. Settings-driven bounds.** `max_iterations` and `max_output_tokens` come from `settings.yaml`
via `Tasks::Player`, resolved through a three-tier fallback: explicit constructor arg → task
settings → class constant. `max_iterations` of 0 or nil disables the ceiling entirely.

---

## 4. Target layout

```
week1_baseline/python/05_agent_loop/
  README.md
  conftest.py                    # copy-forward
  prompts/system.md              # copy-forward (verified unchanged)
  boukensha/
    __init__.py                  # + Agent, LoopError
    agent.py                     # NEW — the whole step
    client.py                    # + tools= passthrough
    prompt_builder.py            # + tools=, + parse_response
    errors.py                    # + LoopError
    config.py                    # copy-forward UNCHANGED (see §9.2)
    backends/
      base.py                    # copy-forward
      {anthropic,openai,gemini,ollama,ollama_cloud}.py   # + parse_response, tools=
    tasks/base.py                # + max_iterations, max_output_tokens, _integer_setting
    …                            # rest copy-forward
  examples/example.py            # NEW — ported from example.rb
  tests/
    test_agent.py                # NEW
    test_backends_*.py           # extended with parse_response cases
    test_tasks.py                # extended
    …
```

Plus `week1_baseline/bin/python/05_agent_loop`.

---

## 5. Ruby → Python semantic gaps new to this step

### 5.1 Symbol keys on the normalized hash

`{ stop_reason: ..., content: ... }` is symbol-keyed in Ruby but the **inner blocks are
string-keyed** (`b["type"]`), because they come from `JSON.parse` without `symbolize_names`. Python
uses strings for both. The asymmetry is invisible in Python — but it means the Ruby reads
`parsed[:stop_reason]` and `block["type"]` in the same method, and a literal transcription must not
"tidy" that into one convention.

### 5.2 `respond_to?` → `hasattr`

`@context.task.respond_to?(:max_iterations)` becomes `hasattr(self._context.task, "max_iterations")`.
Both guard the same case: a task class that predates these settings.

### 5.3 `Integer(value)` is stricter than `int(value)`

Ruby's `Integer("abc")` raises `ArgumentError`; `int("abc")` raises `ValueError`. Closer to the
point, **`Integer("08")` raises in Ruby** (leading zero reads as octal) while `int("08")` returns
`8`. YAML already yields real integers for these keys, so the divergence needs a hand-written
config to surface — but transcribe as `int(...)` and note it rather than reaching for a
compatibility shim.

### 5.4 `to_i` on the explicit override

`resolve_max_iterations` does `explicit.to_i` — Ruby's `to_i` never raises (`"abc".to_i == 0`),
whereas the settings path uses strict `Integer()`. Python's `int()` raises on both. Mirror the
*structure*, and let the stricter behaviour stand: a non-numeric explicit override is a programming
error, and Ruby silently turning it into 0 (which disables the ceiling) is worse.

### 5.5 `positive?` and the disable sentinel

`@max_iterations.positive?` → `self._max_iterations > 0`. Note `0` **disables** the ceiling rather
than meaning "no iterations" — a plain truthiness test would read the same in Python, but spell it
`> 0` to keep the intent legible.

### 5.6 Inclusive ranges

`result.to_s[0..60]` is **61 characters** in Ruby. Python's equivalent is `[:61]`, not `[:60]`.
The trace line is compared in the parity diff, so an off-by-one here shows up as a real failure.

### 5.7 `select` / `map` / `join`

```ruby
content.select { |b| b["type"] == "text" }.map { |b| b["text"] }.join
```

becomes

```python
"".join(b["text"] for b in content if b["type"] == "text")
```

Ruby's bare `join` uses `""` as the separator, not `", "`. Getting this wrong silently corrupts
every multi-block reply.

### 5.8 The heredoc

`<<~MSG.strip` squiggly-heredoc strips leading indentation. Use a module-level string literal
rather than `textwrap.dedent` — the content is fixed and the dedent adds nothing but indirection.
The result must be byte-identical, newlines included, since it is sent to the model.

### 5.9 `tools: []` vs `tools: nil` is load-bearing

`to_payload` does `tools.nil? ? to_tools(context.tools) : tools`. In Python that must be
`if tools is None`, **not** `if not tools` — the wind-down call passes `[]`, and an empty list is
falsy in Python but truthy in Ruby. A literal truthiness translation would re-enable tools on
exactly the call whose purpose is to disable them, which is the single most damaging mistranslation
available in this step.

### 5.10 Trace rendering cannot reach parity

`puts "  tool call → #{name}(#{args})"` interpolates a Ruby Hash, rendering
`{"path" => "README.md"}`. Python's f-string renders the dict as `{'path': 'README.md'}`. Hash
inspect and dict repr simply differ, and matching them would mean hand-rolling a formatter used
by nothing but trace output. **Accepted divergence** — it is the one place the two trees' stdout
is expected to differ, which is worth knowing before comparing live runs by eye.

### 5.11 `rescue ApiError` scope

Ruby's `rescue` sits on the method body, covering the whole of `wrap_up` including
`parse_response` and `extract_text`. Python's `try` must wrap the same span, not just the
`client.call` line.

---

## 6. Implementation steps

1. **Fix the Ruby reference** (§9) and capture the output as the parity baseline.
2. **Copy forward** the step-04 Python package into `05_agent_loop/`, repointing every
   `"""Port of ruby/…"""` docstring at `ruby/05_agent_loop`. Verify `prompts/system.md` matches
   `ruby/05_agent_loop/prompts/` (it should — but check, per step 04's lesson).
3. **`boukensha/errors.py`** — add `LoopError`.
4. **`boukensha/tasks/base.py`** — the two constants, two readers, and `_integer_setting`.
5. **The five backends** — `parse_response` each, plus the `tools` parameter on `to_payload`
   (§5.9). Gemini also gets `_assistant_parts`. Transcribe literally; these are mechanical and the
   risk is transcription error, so §7 asserts whole dicts.
6. **`boukensha/prompt_builder.py`** — `tools` passthrough and the `parse_response` delegator.
7. **`boukensha/client.py`** — `tools` passthrough. Do not touch the retry logic.
8. **`boukensha/agent.py`** — the class. Keep method order and privacy aligned with `agent.rb`.
9. **`boukensha/__init__.py`** — add `Agent`, `LoopError`.
10. **`examples/example.py`** — port line-for-line. Note the tool registration moved *after* the
    agent is constructed, and both tools now resolve paths against `base_dir` (the iteration root)
    rather than the process CWD.
11. **Launcher** — `week1_baseline/bin/python/05_agent_loop`.
12. **Tests** — §7.
13. **READMEs** — the step README, plus a row in `week1_baseline/python/README.md`.

---

## 7. Verification

### 7.1 Offline suite

Carry step 04's suite forward and add:

*`parse_response` per backend* — extend each `test_backends_*.py`
- a text-only reply → `{"stop_reason": "end_turn", "content": [{"type": "text", ...}]}`
- a tool-use reply → `stop_reason == "tool_use"` and a normalized `tool_use` block
- a reply with **both** text and tool_use blocks → `tool_use` wins
- a missing/empty content field → `content == []`, not `None`
- **Gemini**: `functionCall` maps to `tool_use` with `id == name`; missing `args` becomes `{}`;
  `_assistant_parts` round-trips both a bare string and a block list

*`to_payload(tools=...)`* — per backend
- `tools=None` serializes `context.tools`
- `tools=[]` sends an **empty** list — the §5.9 trap. This test is the one that catches a
  truthiness mistranslation, and it must exist for all five backends

*`Agent`* (`test_agent.py`), driven by a stub client returning scripted payloads
- a first reply of `end_turn` returns the joined text and makes exactly one call
- a `tool_use` reply dispatches through the registry, appends assistant + tool_result turns, and
  loops; a following `end_turn` ends it
- multiple `tool_use` blocks in one reply all dispatch, in order
- the iteration counter increments per loop and the trace lines match Ruby's format exactly,
  including the 61-character truncation (§5.6)
- **hitting `max_iterations` triggers exactly one wind-down call**, made with `tools=[]` and
  `max_output_tokens=400`, and does **not** increment the counter
- the wind-down appends `WRAP_UP_DIRECTIVE` as a user turn before calling
- an `ApiError` during wind-down returns the fallback sentence
- an empty/whitespace wind-down reply returns the fallback sentence
- `max_iterations=0` disables the ceiling (§5.5)
- resolution order: explicit arg > task settings > class constant, for both bounds
- a task class lacking `max_iterations` falls back to the constant (§5.2)

*`Tasks::Base`* — extend `test_tasks.py`
- both readers return their defaults when the key is absent
- a string value is coerced (`"10"` → `10`)
- a non-numeric value raises

Then:

```bash
cd week1_baseline/python && ./run-tests && uv run ruff check .
```

### 7.2 First-request payload parity (offline, free)

The loop is non-deterministic, but its **first** request is not. Use step 04's §7.2 technique on
`agent.run`'s opening call to get a byte-for-byte comparison at zero cost — patch `Agent` to print
`builder.to_api_payload(**call_opts)` and exit before the first `client.call`.

Do the same for the **wind-down** payload, which is the one most likely to be mistranslated
(§5.9): construct an agent at its limit and dump the `tools=[], max_output_tokens=400` payload.
`"tools": []` must be present and empty in both trees.

### 7.3 Live run (both trees)

The trace is non-deterministic — iteration count, tool arguments and final prose all vary — so
there is no diff to run. Verify by inspection that both trees:

- print the same header block and the same `[iteration N/25]` / `tool call →` / `tool result →`
  line formats
- dispatch real tools and terminate on `end_turn` rather than exhausting the ceiling
- end with `=== FINAL RESPONSE ===` and a summary of the README

Cost is higher than step 04 — several round-trips per run rather than one. Budget roughly
$0.05–0.15 per tree depending on how many iterations the model takes.

---

## 8. Known drift in the Ruby step-05 reference

- **`LoopError` is declared and never raised.** `errors.rb` defines it and the README documents it
  as "for runaway agents", but `agent.rb` handles the ceiling by winding down rather than raising.
  Mirrored (§1); pin with a test asserting only that it exists and subclasses `Exception`.
- **`MAX_ITERATIONS` is duplicated.** `Agent::MAX_ITERATIONS = 25` and
  `Tasks::Base::DEFAULT_MAX_ITERATIONS = 25` are independent constants holding the same number.
  Transcribe both; do not unify them.
- **`resolve_max_output_tokens` returns `nil` as its final fallback** while its iteration
  counterpart returns a constant, so `Agent::WRAP_UP_OUTPUT_TOKENS` is the only output-token
  default the class applies. `Tasks::Base::DEFAULT_MAX_OUTPUT_TOKENS = 1024` is reached only via
  the settings path.
- **The example's `list_directory` joins with `", "`** where step 04's joined with `"\n"`.
  Intentional-looking, but it is a change; transcribe as-is.

---

## 9. Ruby-side changes required before porting

**Both are blocking. `bundle exec ruby examples/example.rb` currently dies before any API call.**

**9.1 — `BOUKENSHA_DIR` off-by-one (blocking).**
`examples/example.rb:1` resolves three levels up to `week1_baseline/.boukensha`, which does not
exist, so `tasks(:player)` returns nil and `Tasks::Base.provider` raises. This is the same
regression steps 01, 02 and 03 each carry.

```diff
-ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../.boukensha", __dir__)
+ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../../.boukensha", __dir__)
```

**9.2 — `PROMPTS_DIR` off-by-one (blocking).**
`lib/boukensha/config.rb:13` resolves to `week1_baseline/ruby/prompts`, which does not exist. This
is step 04's bug, reintroduced. Left unfixed, `system_prompt` returns nil and the API rejects the
payload with `400 — "system: Input should be a valid array"`.

```diff
-    PROMPTS_DIR = File.expand_path("../../../prompts", __dir__).freeze
+    PROMPTS_DIR = File.expand_path("../../prompts", __dir__).freeze
```

**9.3 — This is the fifth occurrence, and it is expected to recur.** The same class of path
regression has now appeared in steps 01, 02, 03, 04 and 05. A systemic fix was considered and
**explicitly declined** (2026-08-03): patch per step, keep the trees diffable, accept that step 06
will likely need the same two-line fix. Options rejected for now, recorded so the next person does
not re-derive them:

- a Ruby spec asserting both paths resolve to existing directories, so a bad copy-forward fails at
  test time rather than silently at runtime;
- resolving the config dir by walking up for a `.boukensha` directory instead of counting `..`
  segments.

**Both fixes applied and verified 2026-08-03.** Baseline confirmed offline: config resolves to the
repo `.boukensha`, `PROMPTS_DIR` exists, and `system_prompt` returns 181 chars rather than nil.

---

## 10. Notes

- `Agent` takes its collaborators by constructor injection, which is why its tests need no
  patching — unlike `Client`, whose seam is the module-level `urlopen`. Worth preserving if the
  class grows.
- The wind-down path is the most intricate logic in the step and the least likely to be exercised
  by a live run (it needs 25 iterations to trigger). Its tests are the ones that matter.
- With `parse_response` in place the five backends are finally symmetric: each owns both
  directions of its provider's format. Step 03 built the request half; this completes it.
