# 12 · Context Management (Python)

Python port of `week1_baseline/ruby/12_context`.

Step 11 gave the session a face. Step 12 makes it aware of what it costs and whether it still
fits.

## Two ceilings, and they are not the same thing

The mistake this step exists to prevent is conflating them:

| | Question | Field | Trigger |
|---|---|---|---|
| **Window pressure** | Does the conversation still *fit*? | `Context.current_tokens` vs `context_window` | at `compaction_threshold` (0.85) the oldest 40% of messages are dropped |
| **Spend** | What has this turn *cost*? | `Context.turn_tokens` | at `max_turn_tokens` (60k) the agent stops and makes one wind-down call |

One can be tiny while the other is huge: a long turn of small calls spends heavily without ever
filling the window. Step 11 could only count iterations, which measures neither.

`boukensha/models.py` supplies the window from the model id — a model *fact*, never a user
setting. An unknown id falls back to a conservative 32k rather than assuming a large window.

## Also new

- **`reasoning` content blocks.** Each backend normalizes its provider's thinking into one shape
  (`backends/base.py` documents the contract), so the Agent logs model reasoning without knowing
  who produced it. Anthropic sends `thinking`/`redacted_thinking`, Gemini flags a part with
  `thought`, Ollama uses `message.thinking`, OpenAI returns `reasoning` items with a `summary`
  array.
- **New log events** — `reasoning`, `plan`, `compaction`; `prompt` carries `context_window` and
  `turn_end` carries `tokens`.
- **`/compact`** in the REPL, and a colour-coded `ctx 12.4k/200k (6%)` readout in the TUI
  (yellow ≥70%, red ≥85% with a `⚠`).
- **The OpenAI backend moved to the Responses API** (`/v1/responses`). gpt-5.x rejects
  `reasoning_effort` together with tools on chat completions. That changes the system prompt into
  a top-level `instructions` string, messages into `input` items, tool defs into a flat shape, and
  tool results into `function_call_output` items matched by `call_id`.

## Structural change: `boukensha/tasks/` is gone

Step 12 deletes the `Tasks::Base` / `Tasks::Player` hierarchy and reads configuration directly:

```python
cfg.provider_type()              # tasks.player.provider, default "anthropic"
cfg.model()                      # tasks.player.model,    default "claude-haiku-4-5"
cfg.system_prompt                # loaded at construction
cfg.agent_max_iterations()       # 25
cfg.agent_max_output_tokens()    # 1024
cfg.agent_max_turn_tokens()      # 60_000
cfg.agent_compaction_threshold() # 0.85
```

The `tasks.player.*` **settings keys are unchanged** — only the classes went. Per-turn limits move
to a new `agent:` block. `Context` no longer takes a `task`, which is the single largest
mechanical change in the port.

## Differences from the Ruby original

### `usage_pct` rounds half-up explicitly

Ruby's `Float#round` rounds halves away from zero; Python's `round()` uses banker's rounding.

```ruby
(0.5).round   # => 1
```
```python
round(0.5)    # => 0
```

A context at exactly 70.5% would read 71% in Ruby and 70% here — and 70 is precisely where the TUI
turns yellow. `context.py` uses `math.floor(x + 0.5)` so both trees agree. Pinned by
`tests/test_context_window.py`.

### `compact_messages`, not `compact_messages!`

Ruby's bang is not a legal Python identifier; `clear_messages` already dropped it for the same
reason. The arithmetic ports exactly, including the `size - 2` floor and the final `max(_, 0)`
that stops a 0- or 1-message context producing a negative drop.

### Two things restored that upstream's step 12 dropped

- **`execution_metadata`** on the response event — provider, model, `usage_unit`, per-response
  token counts and `cost_usd`. Upstream removed it; `log_viz` renders its cost and model chips
  from exactly those fields, so removing them silently blanks the visualizer. Restored in **both**
  trees. The `task` field is genuinely gone with the task classes.
- **The system-prompt fallback.** `Config` looks in the config directory first and now falls back
  to the `prompts/system.md` shipped with the step. Without it, a `.boukensha` with no `prompts/`
  leaves `system_prompt` as `None` and the agent runs with no instructions at all — silently.

### `list_directory` and `search_files` are disabled

Commented out, matching Ruby: leftovers from when this was a coding harness, of no use to the
player agent. 4 built-in filesystem tools + `run_command` + 34 MCP tools = **39**.

## Run

```sh
week1_baseline/bin/python/12_context              # Textual TUI, with the ctx readout
week1_baseline/bin/python/12_context --no-tui     # plain terminal REPL
week1_baseline/bin/python/12_context --demo       # one-shot example
```

Commands: `/help` `/clear` `/compact` `/quiet` `/loud` `/exit`.

## Test

```sh
cd week1_baseline/python && ./run-tests           # every iteration, isolated
uv run pytest 12_context/tests -q                 # this step only
week1_baseline/mcp/verify-python                  # MCP end-to-end, offline (defaults to this step)
```

547 tests. The step-11 suite carried over minus the 20 task tests, plus new coverage for the model
table, the two counters, the compaction arithmetic (including the 0/1/2-message edge where the
floor and the ceiling fight), the token ceiling, reasoning logging, and the Responses-API shapes.
