# 05 · The Agent Loop (Python)

Python port of `week1_baseline/ruby/05_agent_loop`.

> Requires the shared environment. If you haven't run `uv sync` in `week1_baseline/python`, do
> that first — see [`../README.md`](../README.md).

Step 04 made one call and handed back raw JSON. Step 05 turns that into a conversation that runs
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

`Agent` is provider-agnostic. It only ever sees the normalized shape `parse_response` returns,
which is why nothing in it branches on which backend is in play.

## The normalized response

Every provider disagrees about replies just as they disagree about requests. `parse_response`
collapses them into one contract:

```python
{"stop_reason": "tool_use" | "end_turn",
 "content": [{"type": "text", "text": ...},
             {"type": "tool_use", "id": ..., "name": ..., "input": {...}}]}
```

| Backend | How it decides `stop_reason` | Call id |
|---|---|---|
| `Anthropic` | the API's own `stop_reason` field | the API's `id` |
| `OpenAI` | presence of `tool_calls`, **not** `finish_reason` | the API's `id` |
| `Gemini` | presence of a `functionCall` part | **the function name** — Gemini assigns none |
| `Ollama` / `OllamaCloud` | presence of `tool_calls` | **the function name** |

Gemini also gains a private `_assistant_parts` — the inverse of `parse_response` — because the
agent stores assistant turns as block lists that have to be turned back into Gemini `parts`.

## `Agent`

| Member | Description |
|---|---|
| `Agent(*, context, registry, builder, client, task_settings=None, max_iterations=None, max_output_tokens=None)` | All collaborators injected |
| `run()` | Drives the loop; returns the final text |
| `MAX_ITERATIONS` | `25`. `0` **disables** the ceiling rather than meaning "no iterations" |
| `WRAP_UP_OUTPUT_TOKENS` | `400` — the wind-down call is deliberately short and cheap |
| `WRAP_UP_DIRECTIVE` | The message appended before winding down |

**Limits are trigger thresholds, not hard caps.** On reaching `max_iterations` the agent does not
raise. It appends a directive telling the model to stop calling tools and summarize, then makes
**one** final call with `tools=[]` and a 400-token budget. That call runs *outside* the counted
loop — it cannot re-trigger the limit and does not increment the counter. If it fails with
`ApiError`, or comes back empty, a deterministic fallback sentence is returned instead.

Both bounds resolve through three tiers: explicit constructor argument → task settings
(`settings.yaml`) → class constant.

## Code map

| File | Purpose | Ruby original |
|------|---------|---------------|
| `boukensha/agent.py` | The loop, the ceiling, and the wind-down | `lib/boukensha/agent.rb` |
| `boukensha/backends/*.py` | `parse_response` + the `tools` override on `to_payload` | `lib/boukensha/backends/*.rb` |
| `boukensha/prompt_builder.py` | `parse_response` delegator; `tools` passthrough | `lib/boukensha/prompt_builder.rb` |
| `boukensha/client.py` | `tools` passthrough — retry logic untouched | `lib/boukensha/client.rb` |
| `boukensha/tasks/base.py` | `max_iterations`, `max_output_tokens`, `_integer_setting` | `lib/boukensha/tasks/base.rb` |
| `boukensha/errors.py` | carried forward, plus `LoopError` | `lib/boukensha/errors.rb` |
| `tests/test_agent.py` | 23 tests | *(none — Ruby ships no specs)* |
| everything else | carried forward from step 04 | |

## Differences from the Ruby original

Earlier steps' tables still apply. New here:

| Ruby | Python | Why |
|------|--------|-----|
| `tools.nil? ? to_tools(...) : tools` | `... if tools is None else tools` | **The one that matters.** `[]` is truthy in Ruby and falsy in Python. A natural `if not tools` would re-enable tools on precisely the wind-down call meant to disable them. Pinned by a test on all five backends. |
| `{ stop_reason:, content: }` symbol keys | string keys | The inner blocks are already string-keyed in Ruby (they come from `JSON.parse`), so the Ruby mixes both conventions in one method. Python uses strings throughout. |
| `result.to_s[0..60]` | `str(result)[:61]` | Ruby ranges are **inclusive** — 61 characters, not 60. |
| `content.select{...}.map{...}.join` | `"".join(... for ... if ...)` | Ruby's bare `join` separates with `""`, not `", "`. |
| `Integer(value)` | `int(value)` | Ruby raises on `"08"` (octal); Python returns `8`. YAML yields real integers here, so it needs a hand-written config to surface. |
| `respond_to?(:max_iterations)` | `hasattr(..., "max_iterations")` | Same guard for a task class predating these settings. |
| OpenAI `if message["content"]` | `if message.get("content") is not None` | `""` is truthy in Ruby, so an empty string still yields a text block. Ollama's guard is `content && !content.empty?` and *does* skip it — the two backends genuinely differ, and both are mirrored. |
| `puts "  tool call → #{name}(#{args})"` | `print(f"  tool call → {name}({args})")` | Renders differently: Ruby `{"path" => "README.md"}`, Python `{'path': 'README.md'}`. Hash-inspect vs dict-repr; matching it would mean hand-rolling a formatter for trace output alone. Accepted. |

## Known defects, carried over from Ruby

- **`LoopError` is declared and never raised.** `errors.rb` defines it and the Ruby README
  advertises it "for runaway agents", but the ceiling is handled by winding down, not raising.
- **`MAX_ITERATIONS` is duplicated.** `Agent.MAX_ITERATIONS` and
  `Tasks.Base.DEFAULT_MAX_ITERATIONS` are independent constants holding `25`. Not unified.
- **`_resolve_max_output_tokens` falls back to `None`**, unlike its iteration counterpart which
  falls back to a constant. So `Tasks.Base.DEFAULT_MAX_OUTPUT_TOKENS` is only ever reached through
  the settings path.

Step 03's `PromptBuilder.to_messages()` defect is still present and still pinned.

## Run

```bash
./week1_baseline/bin/python/05_agent_loop
```

> **Makes several billed API calls** — one per iteration. The example typically finishes in two.
> Needs a working `ANTHROPIC_API_KEY` in `.boukensha/.env`.

```
=== BOUKENSHA Step 5: Agent Loop ===

Config: #<Boukensha::Config dir=/Users/you/Sites/Claude-Code-Camp/.boukensha tasks=player>
Provider: anthropic
Model: claude-sonnet-4-6
Max iterations: 25
Max output tokens: 1024

[iteration 1/25]
  tool call → read_file({'path': 'README.md'})
  tool result → # 05 · The Agent Loop (Python)

Python port of `week1_base
[iteration 2/25]

=== FINAL RESPONSE ===
...
```

There is **no output diff to run against Ruby** — the iteration count, tool arguments and final
prose all vary between runs. Parity is checked two other ways:

1. **Payload parity, offline and free.** Both trees build a payload before they POST it, so
   replacing the `agent.run` line with a dump of `builder.to_api_payload()` gives a byte-for-byte
   comparison. Do the same for the wind-down payload (`tools=[], max_output_tokens=400`) — that
   one is the regression detector for the `tools` trap above. Full recipe in the step plan §7.2.
2. **Structural inspection of a live run.** Both trees should print the same header block, the
   same `[iteration N/25]` / `tool call →` / `tool result →` formats, dispatch real tools, and
   terminate on `end_turn` rather than exhausting the ceiling.

## Test

```bash
cd week1_baseline/python
uv run pytest 05_agent_loop
```

269 tests: 204 carried forward from step 04, 23 for `Agent`, and 42 across the backends for
`parse_response` and the `tools` override. All offline.
