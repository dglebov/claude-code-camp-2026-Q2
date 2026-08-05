# Step 11 — A Terminal UI

Boukensha now ships a full terminal UI (TUI) built on the [`charm`](https://github.com/charm-ruby/charm) gem (bubbletea + lipgloss + bubbles). The plain REPL from step 10 is still there and can be selected with `tui: false`.

## What's new

### `Boukensha::Tui`

New class. Wraps a `Repl` instance and replaces its raw `puts`/`gets` I/O with a structured four-zone display:

```
┌──────────────────────────────────────────────┐
│  conversation viewport (scrollable)           │
├──────────────────────────────────────────────┤
│  ⟳ live progress line (hidden when idle)     │
├──────────────────────────────────────────────┤
│  boukensha> input box                         │
├──────────────────────────────────────────────┤
│  status line (always-on)                      │
└──────────────────────────────────────────────┘
```

The **progress line** shows a spinner, current action, iteration counter (`n/MAX`), elapsed seconds, token counts (↑ in / ↓ out), and tool call count while the agent is running. When idle it shows context usage and turn count.

The **status line** always shows: version · model · context tokens used/max · registered tool count · wall-clock time.

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| `Enter` | Submit input or slash command |
| `Esc` | Interrupt the running agent turn |
| `Ctrl+L` | Clear conversation history |
| `PgUp` / `PgDn` | Scroll conversation viewport |
| `Ctrl+C` / `Ctrl+D` | Quit |

The agent runs in a background thread so the UI stays responsive during long turns.

### `Boukensha.repl` — new `tui:` keyword

```ruby
Boukensha.repl(tui: true)   # default — launches charm TUI
Boukensha.repl(tui: false)  # falls back to plain terminal REPL
```

The `--no-tui` CLI flag sets `tui: false` from the command line.

### `Repl` refactored for composability

`Repl` no longer hard-codes `puts`/`gets`. Three methods are now public so `Tui` (or any other front-end) can drive it:

| Method | Purpose |
|--------|---------|
| `on_output(&block)` | Route all REPL output through a callback instead of stdout |
| `handle_command(input)` | Process a slash command; returns `:quit`, `:command`, or `nil` |
| `run_turn(input)` | Run one agent turn and route the result through `on_output` |

`banner`, `logger`, `context`, `model`, and `version` are also exposed as readers.

### `Logger#subscribe`

```ruby
logger.subscribe { |event| ... }
```

Every structured log event (`:iteration`, `:tool_call`, `:tool_result`, `:response`, etc.) is now broadcast to all registered subscribers as well as being written to the JSONL file. `Tui` uses this to update the live progress line in real time without polling.

## Run

From the repo, with no gem install needed:

```sh
week1_baseline/bin/ruby/11_tui              # charm TUI
week1_baseline/bin/ruby/11_tui --no-tui     # plain terminal REPL
week1_baseline/bin/ruby/11_tui --demo       # one-shot example, no session
```

…or from this directory:

```sh
bundle install
bundle exec ruby patches/bubbletea/patch_bubbletea.rb   # see patches/bubbletea/README.md
bundle exec bin/boukensha
bundle exec bin/boukensha --no-tui
```

Keys: `Enter` submit · `ESC` interrupt the turn · `Ctrl+L` clear history · `PgUp`/`PgDn` scroll ·
`Ctrl+C` / `Ctrl+D` quit.

To install globally instead:

```sh
gem uninstall boukensha        # a later step's gem would shadow this one
gem build boukensha.gemspec
gem install boukensha-0.11.0.gem
boukensha                      # config is found by walking up to the nearest .boukensha
```

## MUD tools come from MCP, not a built-in module

Upstream's step 11 branched before step 10's MCP work and shipped the old 480-line
`lib/boukensha/tools/mud.rb` restored. That file is deleted here and all 34 MUD tools are served
by `mud-manager --mcp`, declared under `mcp_servers:` in `settings.yaml` — matching step 10 and
the Python tree (41 tools total, identical names on both sides). Also restored from step 10:
`Tool#required_keys`, `Registry#registered?`, the config walk-up to the nearest `.boukensha`, the
401 message in `client.rb`, and `prompts/` in the gemspec file list.