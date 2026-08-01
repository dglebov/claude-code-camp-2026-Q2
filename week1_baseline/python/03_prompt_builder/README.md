# 03 · The Prompt Builder (Python)

Python port of `week1_baseline/ruby/03_prompt_builder`.

> Requires the shared environment. If you haven't run `uv sync` in `week1_baseline/python`, do
> that first — see [`../README.md`](../README.md).

Every provider wants the same conversation in a different shape. `PromptBuilder` serializes a
`Context` into the exact payload one provider expects, and owns no format knowledge itself —
every method delegates to the backend it was constructed with.

It does **not** call the API. That is step 04.

```
Context (Python objects) → PromptBuilder → Backend → payload (dicts and lists) → POST
```

## `PromptBuilder`

| Method | Description |
|---|---|
| `to_messages()` | Delegates message serialization to the backend |
| `to_tools()` | Delegates tool serialization to the backend |
| `to_api_payload(max_output_tokens=1024)` | Assembles the complete payload, ready to POST |
| `headers()` | The headers this backend needs |
| `url()` | The endpoint this backend posts to |

`to_messages()` is broken for three of the five backends — see [Known
defects](#known-defects-carried-over-from-ruby).

## Backends

Each backend owns its serialization *and* the table of models it supports. Constructing one with
an unlisted model raises `UnsupportedModelError` immediately, so a typo in `settings.yaml` fails
loudly instead of becoming a confusing 400 from the provider.

| | System prompt | Tool schema | Tool result |
|---|---|---|---|
| `Anthropic` | top-level `system` | `input_schema` | `user` message with a `tool_result` block |
| `Gemini` | `systemInstruction.parts` | `functionDeclarations` | `user` message with a `functionResponse` part |
| `OpenAI` | `role: system` in `messages` | `function` envelope | `role: tool` + `tool_call_id` |
| `Ollama` | `role: system` in `messages` | `function` envelope | `role: tool` + `tool_name` |
| `OllamaCloud` | `role: system` in `messages` | `function` envelope | `role: tool` + `tool_name` |

Anthropic and Gemini also disagree with the rest on the assistant's role name — Gemini calls it
`model`.

Each model entry carries `context_window`, `cost_per_million.{input,output}`, `usage_unit`, and
sometimes `usage_level`. Backends expose those plus
`estimate_cost(input_tokens=…, output_tokens=…)`. Local Ollama models cost `0.0`; Ollama Cloud
prices per plan rather than per token, so its costs are `None` and `estimate_cost` returns `None`.

The prices are static tutorial data, current as of June 16, 2026, copied verbatim from the Ruby
tree. Re-pricing them is out of scope for the port.

## Code map

| File | Purpose | Ruby original |
|------|---------|---------------|
| `boukensha/prompt_builder.py` | `PromptBuilder` — delegates to the active backend | `lib/boukensha/prompt_builder.rb` |
| `boukensha/backends/base.py` | Model validation and model metadata | `lib/boukensha/backends/base.rb` |
| `boukensha/backends/{anthropic,openai,gemini,ollama,ollama_cloud}.py` | One per provider format | `lib/boukensha/backends/*.rb` |
| `boukensha/backends/__init__.py` | Package exports | *(none — Ruby requires each file directly)* |
| `prompts/system.md` | The default system prompt | `prompts/system.md` |
| `boukensha/config.py` | carried forward, with `PROMPTS_DIR` restored | `lib/boukensha/config.rb` |
| `boukensha/errors.py` | carried forward, plus `UnsupportedModelError` | `lib/boukensha/errors.rb` |
| everything else | carried forward from step 02, unchanged | |

## Differences from the Ruby original

| Ruby | Python | Why |
|------|--------|-----|
| `unless input_cost && output_cost` | `if input_cost is None or output_cost is None` | **`0.0` is truthy in Ruby and falsy in Python.** Every local Ollama model prices at `0.0`; a literal translation would report unknown cost for all of them. |
| `JSON.pretty_generate` | `json.dumps(..., indent=2, ensure_ascii=False)` | Byte-identical output. `ensure_ascii=False` matters — Ruby emits UTF-8 literally, Python would escape it. |
| `usage_unit: :tokens` | `"tokens"` | Symbols become strings. These values never reach JSON, so the difference is invisible outside the class. |
| `model.inspect` | `f'"{model}"'` | Ruby renders double quotes; `repr()` renders single ones. The error text is compared literally. |
| `const_get(:MODELS)` + `rescue NameError` | `getattr` + `NotImplementedError` | Both find an inherited constant; the base class defines none. |
| `self.model_info(model)` **and** `model_info` | `model_info_for(model)` and `model_info` | Ruby can bind one name to both a class and an instance method. Python cannot. |
| `initialize(host: "…", model:)` | `__init__(self, *, model, host="…")` | Python requires defaults last. Both are keyword-only, so call sites are unaffected. |
| `msg.role == :tool_result` | `msg.role == "tool_result"` | Roles are symbols in Ruby, strings in Python (step 01). |
| `parameters.keys.map(&:to_s)` | `list(tool.parameters)` | Ruby's parameter keys are symbols and need stringifying for JSON; Python's already are strings. |
| `raise ArgumentError` | `raise ValueError` | The example's unsupported-provider guard. |
| `MODELS.freeze` | a plain dict | No Python equivalent; constant by convention, as with `DEFAULT_DIR`. |

## Known defects, carried over from Ruby

`PromptBuilder.to_messages()` passes **one** argument, but `OpenAI`, `Ollama` and `OllamaCloud`
all declare `to_messages(system, messages)`. Calling it with any of those three raises — Ruby
raises `ArgumentError`, Python `TypeError`.

Nothing reaches it in practice: `to_api_payload()` goes through the backend's `to_payload`, which
calls its own `to_messages` with both arguments. The bug is mirrored rather than fixed so the two
trees stay diffable, and `tests/test_prompt_builder.py` pins the behaviour so that fixing it in a
later step is a deliberate change.

## A note on `system`

`Context.system` is populated for the first time since step 00. `Config.PROMPTS_DIR` returns here,
and with no `.boukensha/prompts/player/system.md` on disk the task's override falls through to the
shipped `prompts/system.md`. That text appears verbatim in the payload — note that this file is
**not** the same as step 00's `prompts/system.md`, which carries different wording.

## Run

```bash
./week1_baseline/bin/python/03_prompt_builder
```

Needs `ANTHROPIC_API_KEY` in `.boukensha/.env` (both trees raise without it). It is only used to
build headers, which this step never prints — no secret reaches stdout.

Expected output:

```
=== BOUKENSHA Step 3: Prompt Builder ===

Config: #<Boukensha::Config dir=/Users/you/Sites/Claude-Code-Camp/.boukensha tasks=player>
Provider: anthropic
Model: claude-sonnet-4-6
{
  "model": "claude-sonnet-4-6",
  "system": "You are a MUD player assistant. Use the tools available to you to help the player explore, fight, and interact with the world.",
  "max_tokens": 1024,
  "tools": [
    {
      "name": "look",
      "description": "Look around the current room for details",
      "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
      }
    },
    ...
  ],
  "messages": [
    ...
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "toolu_01X",
          "content": "A damp stone corridor stretches north. Torches flicker on the walls."
        }
      ]
    }
  ]
}
```

Verify parity against Ruby:

```bash
diff <(./week1_baseline/bin/ruby/03_prompt_builder) <(./week1_baseline/bin/python/03_prompt_builder)
```

## Test

```bash
cd week1_baseline/python
uv run pytest 03_prompt_builder
```
