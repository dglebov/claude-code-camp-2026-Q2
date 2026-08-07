# Step 12 — Context Management

When you call an LLM directly you are responsible for the context window. There is no auto-compacting. This step adds proper token tracking, visual warnings, and automatic compaction so the agent never silently blows past the limit.

## What's new

### Accurate context tracking

`Context` now maintains two distinct token counts:

| Attribute | What it measures |
|-----------|-----------------|
| `context_window` | The model's maximum input token capacity (default 200,000 for Anthropic) |
| `current_tokens` | Tokens actually used in the most recent API call (`usage.input_tokens` from the response) |

Previously `token_budget` (8,192) was displayed as the limit — that was the *output* `max_tokens`, not the context window. And the cumulative session token sum was shown as usage, which grew without bound even after `/clear`. Both are fixed.

The Agent updates `current_tokens` after every API response (including mid-turn tool-use calls), so the display always reflects what the next call will actually send.

### Context colour coding

The progress and status lines now colour the context indicator based on how full the window is:

| Usage | Colour | Meaning |
|-------|--------|---------|
| < 70% | Grey | Normal |
| 70–84% | Yellow | Approaching limit |
| ≥ 85% | Red | Compaction imminent |

A `⚠` symbol also appears in the status bar at 85%+.

### Auto-compaction

At the start of each agent turn, if `current_tokens / context_window ≥ 0.85`, the Agent automatically compacts the context before making any API call:

```
[context compacted — 12 messages dropped to free space]
```

Compaction drops the oldest 40% of messages (keeping at least 2) and resets `current_tokens` to 0. The first API call after compaction will report the true new size.

### `Context#compact_messages!`

```ruby
dropped = context.compact_messages!(target_fraction: 0.60)
# => 12  (number of messages dropped)
```

### `/compact` command

Manual compaction from the REPL or TUI:

```
boukensha> /compact
(compacted context — 12 messages dropped)
```

### `Logger#compaction` event

```json
{"phase":"compaction","before":172000,"dropped":12,"context_window":200000}
```

Emitted whenever auto- or manual compaction runs. The TUI subscribes to this event to display the compaction notice in the conversation view.

### `Boukensha.run` / `Boukensha.repl` — `context_window:` keyword

`token_budget:` is replaced by `context_window:` (default `200_000`):

```ruby
Boukensha.repl(context_window: 128_000)  # for a smaller model
```

## Run

From the repo, no gem install needed:

```sh
week1_baseline/bin/ruby/12_context              # charm TUI, with the ctx readout
week1_baseline/bin/ruby/12_context --no-tui     # plain terminal REPL
week1_baseline/bin/ruby/12_context --demo       # one-shot example, no session
```

…or from this directory:

```sh
bundle install
bundle exec ruby patches/bubbletea/patch_bubbletea.rb   # see patches/bubbletea/README.md
bundle exec bin/boukensha
```

Keys: `Enter` submit · `ESC` interrupt · `Ctrl+L` clear · `PgUp`/`PgDn` scroll · `Ctrl+C` quit.
Commands: `/help` `/clear` `/compact` `/quiet` `/loud` `/exit`.

To install globally instead:

```sh
gem uninstall boukensha        # a different step's gem would shadow this one
gem build boukensha.gemspec
gem install boukensha-0.12.0.gem
boukensha                      # config found by walking up to the nearest .boukensha
```

## Carried forward from steps 09–11

Upstream's step 12 branched before that work, so it arrived without any of it. Re-applied here:

- **MUD tools come from MCP, not a built-in module.** `lib/boukensha/tools/mud.rb` is deleted;
  all 34 gameplay tools are served by `mud-manager --mcp`, declared under `mcp_servers:` in
  `settings.yaml`. With the 5 built-ins that is **39 tools** — step 11 had 41, because step 12
  deliberately disables `list_directory` and `search_files` (see `tools/file_system.rb`).
- `Tool#required_keys` and `Registry#tool(required:)`, so MCP optional parameters are not
  advertised to the model as mandatory; `Registry#registered?` for collision detection.
- Config walk-up to the nearest `.boukensha`, so the command works from any subdirectory.
- `/quiet` and `/loud`, the banner `step:` line, and a readable message instead of a backtrace
  when run outside a project.
- macOS portability in `patches/bubbletea/patch_bubbletea.rb` (BSD `strip`, and `.bundle` rather
  than `.so` — the latter silently installed a file Ruby never loads).
- The 401 message in `client.rb`, and `prompts/` in the gemspec file list.

### One step-12 specific fix

`Config#load_system_prompt` reads only from the *config* directory. Our `.boukensha/` has no
`prompts/`, so `system_prompt` was `nil` and the agent ran with no instructions at all — silently.
Step 11 got a fallback via `Tasks::Base`; step 12 deleted the task classes, so `PROMPTS_DIR` and a
bundled `prompts/system.md` are restored here and `load_system_prompt` falls back to them.
