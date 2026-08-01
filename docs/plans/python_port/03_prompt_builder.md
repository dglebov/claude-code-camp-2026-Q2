# Python Port Plan — Step 03 · The Prompt Builder

Port `week1_baseline/ruby/03_prompt_builder` to `week1_baseline/python/03_prompt_builder`.

**Scope:** week1 only, step 03 only. Builds on the completed step-02 port; reuses the shared
environment at `week1_baseline/python/` (no new venv, no new dependencies).

**Prerequisites:** the Ruby reference is currently broken in two ways and both must be fixed
before there is a baseline to prove parity against — see §9.

This is a much larger step than 02. Nine new modules (a builder, a backend base, five backends, a
package init, a prompt file) against 02's two.

---

## 1. Decisions (settled — do not re-litigate)

| Decision | Choice |
|----------|--------|
| `settings.yaml` says `model: claude-sonet-5` | **Fix the config** to `claude-sonnet-4-6` (§9.3). Misspelled, and absent from the MODELS table, so the backend refuses to initialize — which is exactly the guard this step exists to demonstrate. Both trees read the same file, so parity is preserved automatically. |
| Broken Ruby reference | **Fix Ruby first**, then port. Same `BOUKENSHA_DIR` path fix as steps 00–02 (§9.1). |
| `PromptBuilder#to_messages` arity bug | **Mirror it, flag it.** Port as-is so Python raises in the same place; record in §8. Same treatment as `token_budget` (01) and tools-on-Context (02). |
| JSON rendering | `json.dumps(payload, indent=2, ensure_ascii=False)`. **Verified byte-identical** to Ruby's `JSON.pretty_generate` on this payload. |
| Ruby-namespaced error text | **Keep it.** `Boukensha::Backends::Anthropic does not support model …` stays literal, as `#<Boukensha::Config …>` already does (§5.5). |
| Structure | Mirror Ruby 1:1, as in steps 00–02. |
| Environment | Shared `week1_baseline/python/.venv`. `json` is stdlib. |

---

## 2. Reference files — what to port

Source of truth is `week1_baseline/ruby/03_prompt_builder/`.

### New in this step — the actual work

| Read this | Purpose | Becomes |
|---|---|---|
| `lib/boukensha/prompt_builder.rb` | Thin delegator: `to_messages`, `to_tools`, `to_api_payload`, `headers`, `url` | `boukensha/prompt_builder.py` |
| `lib/boukensha/backends/base.rb` | Model table lookup, validation, cost/window metadata | `boukensha/backends/base.py` |
| `lib/boukensha/backends/anthropic.rb` | `system` top-level, `input_schema` tools, tool results as user messages | `boukensha/backends/anthropic.py` |
| `lib/boukensha/backends/openai.rb` | system in `messages`, `function`-wrapped tools, `role: tool` + `tool_call_id` | `boukensha/backends/openai.py` |
| `lib/boukensha/backends/gemini.rb` | `systemInstruction`/`contents`/`parts`, `functionDeclarations`, `assistant` → `model` | `boukensha/backends/gemini.py` |
| `lib/boukensha/backends/ollama.rb` | like OpenAI but `tool_name`, `stream: false`, local host URL | `boukensha/backends/ollama.py` |
| `lib/boukensha/backends/ollama_cloud.rb` | like Ollama with an API key and `nil` pricing | `boukensha/backends/ollama_cloud.py` |
| `prompts/system.md` | The default system prompt. **Copy from `ruby/03_prompt_builder/` — see §5.10.** | `03_prompt_builder/prompts/system.md` |
| `examples/example.rb` | Smoke test; its output is the parity target | `examples/example.py` |
| `README.md` | Per-backend format tables — genuinely useful, and accurate this time | `03_prompt_builder/README.md` (adapted) |

Ruby has no `backends/__init__.py` equivalent; Python needs one, mirroring the existing
`tasks/__init__.py`.

### Changed vs step 02 — small, targeted edits

| File | Delta |
|---|---|
| `boukensha/config.py` | **Restore `PROMPTS_DIR`**, dropped back in step 01. `ruby/03_prompt_builder/lib/boukensha/config.rb` is byte-identical to `ruby/00_config`'s, so take the line verbatim from `python/00_config/boukensha/config.py`. |
| `boukensha/errors.py` | **Add `UnsupportedModelError`.** |
| `boukensha/__init__.py` | **Extend** — add `PromptBuilder`, `UnsupportedModelError`, and the `backends` subpackage. |
| `tests/test_config.py` | **Restore** `test_prompts_dir_constant_points_at_shipped_prompts`, verbatim from `python/00_config`. |

### Carried forward from step 02 — unchanged

`boukensha/tool.py`, `message.py`, `context.py`, `registry.py`, `env_file.py`, `tasks/` (all
three files), `conftest.py`, and `tests/{test_tasks,test_tool,test_message,test_context,test_registry}.py`.

Confirmed by `diff -rq ruby/02_the_registry ruby/03_prompt_builder`: outside the new files, only
`config.rb`, `errors.rb`, `lib/boukensha.rb`, the README and the example differ. `context.rb`
"differs" solely by gaining a trailing newline.

### Context only — do not port

- `week1_baseline/ITERATIONS.md` §3 — design intent, including the note that response
  normalization arrives in step 05, not here.
- `docs/plans/python_port/{00_config,01_struct_skeleton,02_the_registry}.md` — §5 of each still
  applies in full.

---

## 3. What step 03 actually adds

`PromptBuilder` serializes a `Context` into the exact shape each provider's REST API expects. It
does **not** call the API — that is step 04. It owns no format knowledge itself; every method
delegates to the backend it was constructed with.

```
Context (Python objects) → PromptBuilder → Backend → payload (plain dicts/lists) → POST
```

`Backends::Base` adds a second job that is easy to miss: each backend owns a table of the models
it supports, and **refuses to initialize on an unknown one**. That is what turns a typo in
`settings.yaml` into an immediate `UnsupportedModelError` instead of a confusing 400 from the API.
Each entry carries `context_window`, `cost_per_million.{input,output}`, `usage_unit`, and
optionally `usage_level`.

| Backend | System prompt | Tool schema | Tool result |
|---|---|---|---|
| Anthropic | top-level `system` | `input_schema` | `user` message with a `tool_result` block |
| Gemini | `systemInstruction.parts` | `functionDeclarations` | `user` message with a `functionResponse` part |
| OpenAI | `role: system` in `messages` | `function` envelope | `role: tool` + `tool_call_id` |
| Ollama / OllamaCloud | `role: system` in `messages` | `function` envelope | `role: tool` + `tool_name` |

---

## 4. Target layout

```
week1_baseline/python/03_prompt_builder/
  README.md
  conftest.py                    # copy-forward
  prompts/
    system.md                    # NEW — from ruby/03, NOT from python/00 (§5.10)
  boukensha/
    __init__.py                  # extended
    config.py                    # copy-forward + PROMPTS_DIR restored
    env_file.py                  # copy-forward
    tool.py                      # copy-forward
    message.py                   # copy-forward
    context.py                   # copy-forward
    errors.py                    # + UnsupportedModelError
    registry.py                  # copy-forward
    prompt_builder.py            # NEW
    backends/
      __init__.py                # NEW
      base.py                    # NEW
      anthropic.py               # NEW
      openai.py                  # NEW
      gemini.py                  # NEW
      ollama.py                  # NEW
      ollama_cloud.py            # NEW
    tasks/
      __init__.py  base.py  player.py    # copy-forward
  examples/
    example.py
  tests/
    test_config.py               # copy-forward + PROMPTS_DIR test restored
    test_tasks.py  test_tool.py  test_message.py  test_context.py  test_registry.py   # copy-forward
    test_prompt_builder.py       # NEW
    test_backends_base.py        # NEW
    test_backends_anthropic.py   # NEW
    test_backends_openai.py      # NEW
    test_backends_gemini.py      # NEW
    test_backends_ollama.py      # NEW
    test_backends_ollama_cloud.py # NEW
```

One test module per source module, matching the existing convention.

---

## 5. Ruby → Python semantic gaps new to this step

§5 of the step-00, 01 and 02 plans still applies. These are **additional**.

**5.1 — `0.0` is truthy in Ruby and falsy in Python. The highest-risk item in this step.**

```ruby
return nil unless input_token_cost_per_million && output_token_cost_per_million
```

Every local Ollama model has `cost_per_million: { input: 0.0, output: 0.0 }`. In Ruby that guard
passes and `estimate_cost` returns `0.0`. A literal Python translation (`if not input_cost`)
would return `None` for every Ollama model. Use `is None` checks:

```python
if input_cost is None or output_cost is None:
    return None
```

OllamaCloud genuinely uses `nil`/`None` for both, so the guard must still fire there. A test must
cover both cases or this passes silently.

**5.2 — Symbol keys in the model tables become strings.**
`{ context_window: 200_000, cost_per_million: { input: 1.0, output: 5.0 }, usage_unit: :tokens }`
becomes a plain dict with string keys, and `usage_unit: :tokens` becomes `"tokens"`. These values
never reach JSON — they are only exposed through the accessors — so the symbol/string difference
is invisible outside the class. Note it in the README differences table.

**5.3 — `fetch` vs `[]` on model info.**
`model_info.fetch(:context_window)` raises `KeyError` when absent; `model_info[:usage_level]`
returns `nil`. Python: `self._model_info["context_window"]` and
`self._model_info.get("usage_level")` respectively. Do not collapse both to `.get`.

**5.4 — `const_get(:MODELS)` → a class attribute.**

```ruby
def self.models
  const_get(:MODELS)
rescue NameError
  raise NotImplementedError, "#{self} must define MODELS"
end
```

Python equivalent is `getattr(cls, "MODELS", None)`, raising `NotImplementedError` when it is
missing. Both forms find an inherited constant, and `Base` defines none, so `Base.models()` raises
in both trees.

**5.5 — `model.inspect` renders double quotes; `repr()` renders single.**
`"#{name} does not support model #{model.inspect}"` produces `… model "claude-sonet-5". …`.
Python's `repr()` would give `'claude-sonet-5'` — wrong quote character. Interpolate explicitly:
`f'... does not support model "{model}". ...'`.

`name` is the Ruby class name, `Boukensha::Backends::Anthropic`. Keep that exact string in Python
via `f"Boukensha::Backends::{cls.__name__}"` — the tree already reproduces Ruby-namespaced strings
verbatim in `Config.__str__` (`#<Boukensha::Config …>`) and in step 02's `UnknownToolError`
message. Step 04+ may surface these errors on stdout, and parity is cheaper to keep than to
retrofit.

**5.6 — Roles are symbols in Ruby, strings in Python.**
Backends branch on `case msg.role … when :tool_result` / `when :assistant`. The Python `Message`
stores plain strings (step-01 §5.7), so compare against `"tool_result"` / `"assistant"`. Behaviour
is identical because Ruby's example only ever passes symbols and Python's only ever strings.
`msg.role.to_s` in the else branch becomes just `msg.role`.

**5.7 — Optional-before-required keyword arguments.**
`def initialize(host: "http://localhost:11434", model:)` is legal Ruby. Python requires defaults
last: `def __init__(self, *, model, host="http://localhost:11434")`. Both are keyword-only, so
call sites are unaffected.

**5.8 — Dict insertion order is payload key order.**
Ruby hash literals and Python dicts both preserve insertion order, and the payload is compared
byte-for-byte after `pretty_generate`. Transcribe every literal in its original order — `model`,
`system`, `max_tokens`, `tools`, `messages` for Anthropic — and do not sort anything.

**5.9 — `JSON.pretty_generate` → `json.dumps(..., indent=2, ensure_ascii=False)`.**
Verified byte-identical on this step's payload, including inline `{}` / `[]` for empties and
one-element-per-line arrays. `ensure_ascii=False` is not optional: Ruby emits UTF-8 literally,
while Python's default would escape non-ASCII to `\uXXXX`. Nothing in this example is non-ASCII,
so a wrong setting would pass here and break later.

**5.10 — `prompts/system.md` differs between step 00 and step 03. Do not copy the wrong one.**
`ruby/00_config/prompts/system.md` (249 bytes, starts "You are MUD journet Player agent…") is not
`ruby/03_prompt_builder/prompts/system.md` (127 bytes, "You are a MUD player assistant…").
`python/00_config/prompts/system.md` matches the step-00 text. The system prompt is echoed
verbatim in the payload, so copying step 00's file silently breaks parity. Copy from
`ruby/03_prompt_builder/prompts/system.md`.

**5.11 — `tool.parameters.keys.map(&:to_s)` → `list(tool.parameters)`.**
Ruby's parameter hashes use symbol keys and must be stringified for JSON. Python's are already
strings. Note that this is the JSON `required` array — unrelated to step 01's `[:direction]`
display helper, which stays as-is.

**5.12 — `raise ArgumentError` in the example → `ValueError`.**
The example's unsupported-provider guard is a plain argument error, not a Boukensha one.

**5.13 — `MODELS.freeze` has no Python equivalent.**
A module/class-level constant by convention, same as `DEFAULT_DIR.freeze` in step 00. Not worth a
`MappingProxyType`.

---

## 6. Implementation steps

1. **Fix the Ruby reference and the config** (§9) and capture the output as the parity baseline.
2. **Copy forward** the step-02 Python package into `03_prompt_builder/`, repointing the
   `"""Port of ruby/…"""` docstring paths at `ruby/03_prompt_builder` as in previous steps.
3. **`prompts/system.md`** — copy from `ruby/03_prompt_builder/prompts/` (§5.10).
4. **`boukensha/config.py`** — restore `PROMPTS_DIR`; restore its test in `tests/test_config.py`.
5. **`boukensha/errors.py`** — add `UnsupportedModelError`.
6. **`boukensha/backends/base.py`** — model table access, `validate_model!` → `validate_model`,
   the metadata accessors, and `estimate_cost` with §5.1's `is None` guard.
7. **The five backends** — transcribe each `to_messages` / `to_tools` / `to_payload` / `headers` /
   `url` literally, preserving key order (§5.8). These are mechanical; the risk is transcription
   error, so the tests in §7 assert whole payloads rather than spot-checking fields.
8. **`boukensha/backends/__init__.py`** — export `Base` and the five backends, mirroring
   `tasks/__init__.py`.
9. **`boukensha/prompt_builder.py`** — five delegating methods, including the broken
   `to_messages` (§8).
10. **`boukensha/__init__.py`** — extend to mirror `lib/boukensha.rb`'s twelve requires: existing
    exports plus `PromptBuilder`, `UnsupportedModelError`, and the `backends` module (so the
    example reads `backends.Anthropic(...)`, mirroring `Boukensha::Backends::Anthropic`).
11. **`examples/example.py`** — port line-for-line: register `look` (no parameters) and `move`,
    add three messages including the `tool_result` one, select the backend by provider, then print
    the four lines and the pretty payload.
12. **Launchers** — `bin/ruby/03_prompt_builder` and `bin/python/03_prompt_builder`.
13. **Tests** — §7.
14. **READMEs** — the step README, plus a row in `week1_baseline/python/README.md`.

---

## 7. Verification

**Output parity (primary acceptance test).**

```bash
diff <(./week1_baseline/bin/ruby/03_prompt_builder) <(./week1_baseline/bin/python/03_prompt_builder)
```

Silence means parity. Target output, captured from the Ruby reference with §9's fixes applied
(payload abbreviated here — the full 60-line block is what the diff compares):

```
=== BOUKENSHA Step 3: Prompt Builder ===

Config: #<Boukensha::Config dir=/Users/dglebov/claude-code-camp-2026-Q2/.boukensha tasks=player>
Provider: anthropic
Model: claude-sonnet-4-6
{
  "model": "claude-sonnet-4-6",
  "system": "You are a MUD player assistant. Use the tools available to you to help the player explore, fight, and interact with the world.",
  "max_tokens": 1024,
  "tools": [
    { "name": "look",  … "input_schema": { "type": "object", "properties": {}, "required": [] } },
    { "name": "move",  … "required": [ "direction" ] }
  ],
  "messages": [
    { "role": "user",      "content": "I just arrived in the dungeon. …" },
    { "role": "assistant", "content": "Let me take a look around first." },
    { "role": "user",      "content": [ { "type": "tool_result", "tool_use_id": "toolu_01X", … } ] }
  ]
}
```

Note the example needs `ANTHROPIC_API_KEY` present (`ENV.fetch` / `os.environ[...]` both raise
without it). It is only used to build headers, which this step never prints — no secret reaches
stdout.

**pytest coverage.** Carry the step-02 suite forward (restoring the `PROMPTS_DIR` test), and add:

*Backends::Base* (`test_backends_base.py`)
- `Base.models()` raises `NotImplementedError` (§5.4)
- `validate_model` returns the name for a known model, including a non-string input
- unknown model raises `UnsupportedModelError` with the exact Ruby text, double quotes and
  alphabetically sorted supported list included (§5.5)
- `context_window` / `usage_unit` come from the table; a missing `context_window` raises
  `KeyError`; `usage_level` returns `None` when absent (§5.3)
- **`estimate_cost` returns `0.0`, not `None`, for a zero-cost model** (§5.1)
- `estimate_cost` returns `None` when either side is `None`
- a normal cost computes correctly: `(in*cost_in + out*cost_out) / 1_000_000`

*Each backend* (one module each)
- constructing with a model outside its table raises `UnsupportedModelError`
- `to_tools` output matches the README's documented shape exactly, for both a no-parameter tool
  (`look`) and a parameterised one (`move`), including `required`
- `to_messages` maps user / assistant / tool_result correctly — Gemini's `assistant` → `model`,
  Anthropic's tool result wrapped in a `user` message, OpenAI's `tool_call_id` vs Ollama's
  `tool_name`
- `to_payload` equals the full expected dict, key order included
- `headers` and `url` (Gemini interpolates the model into the URL; Ollama uses the host)
- Ollama's default host, and that a custom `host` changes `url`

*PromptBuilder* (`test_prompt_builder.py`)
- `to_tools`, `to_api_payload`, `headers`, `url` all delegate to the backend
- `to_api_payload` honours a custom `max_output_tokens`
- `to_messages` works with Anthropic/Gemini and **raises `TypeError` with OpenAI/Ollama/
  OllamaCloud** — pin the §8 bug so a later step's fix is a deliberate change, not a surprise

Run `uv run pytest 03_prompt_builder`, then `./run-tests` for all four iterations, then
`uv run ruff check .`.

---

## 8. Known drift in the Ruby step-03 reference

Port the **code**, not the docs. Recording these so they are not mistaken for port bugs:

- **`PromptBuilder#to_messages` is broken for three of the five backends.** It passes one argument;
  OpenAI, Ollama and OllamaCloud all declare `to_messages(system, messages)`. `to_api_payload`
  calls `to_payload`, which calls the backend's own `to_messages` with both arguments, so the
  example never trips it. Mirrored deliberately (§1), pinned by a test (§7).
- `tasks/base.rb:9,13` still say `settings.yml` in error text where the file is `settings.yaml`.
  Carried forward unchanged since step 00; the Python tree says `settings.yaml`.
- README run instructions say `./week1_baseline/bin/03_prompt_builder`; the real path after the
  bin restructure is `./week1_baseline/bin/ruby/03_prompt_builder`.
- The README's model-price table is explicitly "static tutorial data, current as of June 16,
  2026". The Python port copies the numbers verbatim; it is not the port's job to re-price them.
- The model tables list models that do not exist outside this course (`claude-opus-4-8`,
  `gpt-5.5`, `gemma4`, …). Transcribe them exactly; correcting them would break parity and is not
  in scope.

---

## 9. Ruby-side and config changes required before porting

**9.1 — Fix the config-dir path (blocking).**
`ruby/03_prompt_builder/examples/example.rb:1` resolves three levels up to
`week1_baseline/.boukensha`, which does not exist, so `tasks(:player)` returns nil and
`Tasks::Base.fetch` raises `NoMethodError`. Confirmed by running it. The same regression has now
appeared in steps 01, 02 and 03.

```diff
-ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../.boukensha", __dir__)
+ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../../.boukensha", __dir__)
```

**9.2 — Add the missing launchers.**
No `bin/ruby/03_prompt_builder` or `bin/python/03_prompt_builder` exists. Create both, mirroring
the `02_the_registry` pair, and `chmod +x`.

**9.3 — Fix the model in `.boukensha/settings.yaml` (blocking, Q1-approved).**
`claude-sonet-5` is misspelled and absent from `Anthropic::MODELS`, so the backend refuses to
initialize:

```
Boukensha::Backends::Anthropic does not support model "claude-sonet-5".
Supported models: claude-haiku-4-5, claude-haiku-4-5-20251001, claude-opus-4-8, claude-sonnet-4-6
```

```diff
 tasks:
   player:
     provider: anthropic
-    model: claude-sonet-5
+    model: claude-sonnet-4-6
```

This is the user's config directory, not repository code — but both trees read the same file, so
it cannot cause a parity divergence. Steps 00–02 never read `model`, so nothing already ported
is affected.

**9.4 — Flagged, not fixed.** Everything in §8.

---

## 10. Notes

- No new Python dependencies. `json` is stdlib; `pyproject.toml` is untouched.
- `Context.system` is non-`None` for the first time since step 00: `PROMPTS_DIR` returns, and with
  no `.boukensha/prompts/player/system.md` present the override falls through to the shipped
  default. The prompt text is visible in the payload, which is why §5.10 matters.
- This step still does not call an API and does not normalize responses. `ITERATIONS.md` places
  response normalization in step 05, despite §3 of that document describing it as a prompt-builder
  concern.
- The five backends are ~80 lines each of near-identical structure. Resist factoring their shared
  `to_tools` into a mixin — the Ruby duplicates it deliberately so each provider's format is
  readable in one file, and diverging would make the trees harder to diff.
