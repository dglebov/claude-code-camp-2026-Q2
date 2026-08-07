# Step 12 (`12_context`) — carrying the 09–11 work forward

Reference: `week1_baseline/ruby/12_context/` (untracked, upstream as-shipped)
Baseline:  `week1_baseline/ruby/11_tui/` (ours, fixed and shipping)

Step 12 branched from *upstream's* step 11, so it arrives without a single fix from steps 09–11.
This plan preserves everything step 12 genuinely adds and re-applies everything it dropped.

> **Status: awaiting review.** Four questions in §4 change what gets built. Answer them inline,
> then say execute.

---

## 1. What step 12 actually adds

Real content, all of it worth keeping:

| Area | What's new |
|---|---|
| `lib/boukensha/models.rb` **(new, 21 lines)** | `Models::TABLE` — model id → `context_window`. Unknown ids fall back to a conservative 32k rather than assuming a large window. |
| `lib/boukensha/context.rb` | Context-window awareness: `context_window`, `current_tokens`, `turn_tokens`, `compaction_threshold`, `usage_fraction`, `usage_pct`, `needs_compaction?`, `compact_messages!` (drops the oldest 40%, keeps ≥2), `update_tokens`, `reset_turn_tokens`, `add_turn_tokens`. |
| `lib/boukensha/agent.rb` | A **second** ceiling — `max_turn_tokens` (spend budget) alongside `max_iterations`; `compact_if_needed` before each call; `record_usage`; `log_reasoning`; a `plan` event for preamble text that accompanies a tool call. |
| `lib/boukensha/backends/*.rb` (all 5) | A normalized `"reasoning"` content block in the response contract, documented in `backends/base.rb`, alongside `"text"` and `"tool_use"`. |
| `lib/boukensha/logger.rb` | New events: `reasoning`, `plan`, `compaction`. `prompt` gains `context_window`; `turn_end` gains `tokens`. |
| `lib/boukensha/tui.rb` | Context-usage readout — `ctx 12.4k/200k (6%)` in both the idle line and the status bar, colour-coded (yellow ≥70%, red ≥85%) with a `⚠` at the alert threshold. Also a textarea width fix. |
| `lib/boukensha/config.rb` | **A deliberate redesign** — see §3. |

## 2. What it dropped

Every item below is ours, from steps 09–11. Verified by inspection, not assumed:

| # | Lost | Consequence if shipped as-is |
|---|---|---|
| 1 | `lib/boukensha/mcp/`, `tools/mcp.rb` | No MCP at all; `mcp_servers:` in settings.yaml silently ignored |
| 2 | `tools/mud.rb` **restored** (480 lines) | 27 built-in tools duplicating the MCP-served set, and a second login racing the MCP session |
| 3 | `Tool#required_keys`, `Registry#tool(required:)` | MCP optional params advertised to the model as mandatory |
| 4 | `Registry#registered?` | Tool-name collision detection gone |
| 5 | Config walk-up to nearest `.boukensha` | Back to `~/.boukensha` only — reverses the change you specifically asked for |
| 6 | `client.rb` 401 message | Generic failure instead of "check your API key" |
| 7 | `Boukensha.quiet!/loud!/quiet?` + `/quiet` `/loud` | Commands vanish from the REPL and `HELP` |
| 8 | `missing_config_message` | Raw backtrace again when run outside a project |
| 9 | Banner `step:` line | No way to tell which of 13 copies is running |
| 10 | `patch_bubbletea.rb` portability | Fails on macOS: GNU `strip --strip-debug`, and `.so` where the linker emits `.bundle` — the second silently installs a file Ruby never loads |
| 11 | `gemspec` shipping `prompts/` | Moot for step 12 — see Q1 |

Plus three `check-paths` failures:

```
FAIL 12_context  not executable: bin/boukensha
FAIL 12_context  BOUKENSHA_DIR -> week1_baseline/.boukensha (does not exist)
FAIL 12_context  launcher missing or not executable: bin/ruby/12_context
```

`PROMPTS_DIR` is *not* flagged only because step 12 deleted the constant.

**Not affected:** the `mud_manager` fixes (take-over login, drain-on-reconnect, daemon shutdown) live in
`week0_explore/mud_manager`, are installed as 0.2.3, and are independent of which step runs.

## 3. The one thing NOT to restore: `tasks/`

Step 12 deletes `lib/boukensha/tasks/` (`Tasks::Base`, `Tasks::Player`) and replaces the whole
abstraction with direct `Config` readers:

```ruby
cfg.provider_type   # dig(:tasks, :player, :provider) || "anthropic"
cfg.model           # dig(:tasks, :player, :model)    || "claude-haiku-4-5"
cfg.system_prompt   # loaded at Config#initialize
cfg.agent_max_iterations        # default 25
cfg.agent_max_output_tokens     # default 1024
cfg.agent_max_turn_tokens       # default 60_000
cfg.agent_compaction_threshold  # default 0.85
```

The `tasks.player.*` **settings keys stay**; only the class hierarchy is gone, and limits move to a
new `agent:` block. This is a coherent simplification, not an accident — restoring `tasks/` would
fight it and leave two config paths.

**Recommendation: accept the redesign.** Carry forward only what is orthogonal to it — which is
everything in §2 except item 11.

## 4. Open questions

### Q1. Step 12 currently runs with **no system prompt at all** *(recommend: bundle a default)*

`Config#load_system_prompt` reads only from the config directory:

```ruby
.boukensha/prompts/player/system.md   # when prompt_override.system == true
.boukensha/prompts/system.md          # otherwise
# neither exists -> nil
```

Our `.boukensha/` has **no `prompts/` directory**, and `settings.yaml` sets
`prompt_override: {system: true}`. So `cfg.system_prompt` returns `nil` and the agent runs with an
empty system prompt. Step 11 could not hit this — `Tasks::Base.prompt` falls back to the step's
bundled `prompts/system.md`.

This is silent. Nothing warns; the agent just gets no instructions.

Three ways out:

| Option | Effect |
|---|---|
| **A (recommended)** — bundle `12_context/prompts/system.md` (copy step 11's) and add a fallback to it in `load_system_prompt`, restoring the `PROMPTS_DIR` constant and the gemspec entry | Matches step 11 behaviour; installed gem works standalone; fixes item 11 as a side effect |
| B — create `.boukensha/prompts/system.md` in the repo config dir | One file, no code change, but an installed gem still has no default and every new project must remember to add one |
| C — leave it and add a startup warning | Honest, but the agent is still unprompted |

### Q2. Add an `agent:` block to `.boukensha/settings.yaml`? *(recommend: yes, explicitly)*

The defaults are reasonable, so nothing breaks without it. But `max_turn_tokens: 60_000` is a real
spend ceiling that now silently applies, and `compaction_threshold: 0.85` changes behaviour on long
sessions. Writing them down makes both visible and tunable:

```yaml
agent:
  max_iterations: 25
  max_output_tokens: 1024
  max_turn_tokens: 60000
  compaction_threshold: 0.85
```

Both trees read this file, so it must stay harmless to step 11 — it is: step 11 ignores unknown
top-level keys.

### Q3. Python port of step 12 — now or later? *(recommend: later, separate plan)*

You asked for Ruby. Step 12 is a substantial port (Models, Context token tracking, compaction,
reasoning blocks across 5 backends, the TUI readout) and deserves its own
`docs/plans/python_port/12_context.md`. Flagging so the trees don't silently drift — Python is
currently at step 11.

### Q4. Rebuild and reinstall the gem at 0.12.0? *(recommend: yes, at the end)*

`version.rb` already says `0.12.0`. The globally installed `boukensha` is 0.11.0. Same two-step as
last time: `gem build` then uninstall/install. Only after §5 and §6 pass.

---

## 5. Implementation steps

Ordered so the tree is loadable at each stage.

| # | Task |
|---|---|
| 1 | `git add` the directory first — it is untracked, so there is currently no diff to review against |
| 2 | Copy from step 11, unchanged (our fixes, no step-12 content): `lib/boukensha/tool.rb`, `registry.rb`, `client.rb`, `tools/mcp.rb`, `lib/boukensha/mcp/` |
| 3 | Delete `lib/boukensha/tools/mud.rb` |
| 4 | `config.rb` — **merge, do not copy.** Keep step 12's `provider_type`/`model`/`system_prompt`/`agent_*`; re-add `find_project_dir` + the three-tier `resolve_dir`, and `mcp_servers` + `normalize_server` |
| 5 | `lib/boukensha.rb` — **merge.** Keep step 12's `Models.context_window`, `Context.new(context_window:, compaction_threshold:)`, `max_turn_tokens:`; re-add `quiet!/loud!/quiet?`, `Tools::Mcp.register_all` + client close in `ensure`, `missing_config_message`; drop `Tools::Mud` wiring and `mud_opts_from_config`; keep the `require_relative` for `models` and the rescued `tui` require |
| 6 | `repl.rb` — **merge.** Keep step 12's content; re-add `/quiet` `/loud` to `handle_command` and `HELP`, the banner `step:` line, and drop `mud_status_string`/`probe_mud` |
| 7 | `boukensha_loader.rb` — re-apply the step-11 version (it already has `--no-tui`); remove the `repl_opts[:mud]` path that would raise `ArgumentError` |
| 8 | `patches/bubbletea/patch_bubbletea.rb` — re-apply the DLEXT + `strip` portability fix |
| 9 | `examples/example.rb` — fix `BOUKENSHA_DIR` depth (3 → 4 levels) and the step-10 header |
| 10 | `chmod +x bin/boukensha`; create `week1_baseline/bin/ruby/12_context` |
| 11 | Q1 (system prompt) and Q2 (`agent:` block) per your answers |
| 12 | `bundle install`; regenerate `Gemfile.lock` if it pins a removed `mud_manager` (step 11 needed `bundle lock --add-platform arm64-darwin`); re-apply the bubbletea patch |
| 13 | `README.md` — document the carry-forward, as step 11's does |

## 6. Verification

| Check | Expectation |
|---|---|
| `week1_baseline/bin/ruby/check-paths` | all steps clean |
| `week1_baseline/mcp/verify` | 35/35 |
| `bin/ruby/12_context --no-tui`, scripted `/help` + `/exit` | banner with `step: 12_context`, `/quiet` and `/loud` listed |
| Tool count | 41, and the tool-name list identical to step 11's |
| Banner diff vs step 11 | version line only |
| TUI under a pty (120×40) | four zones, and the new `ctx N/M (P%)` readout |
| Context tracking | after one real turn, `ctx` is non-zero and `usage_pct` matches |
| Compaction | force `compaction_threshold: 0.01`, run two turns, assert a `compaction` event lands in the JSONL |
| Missing config | run from `/tmp` → readable message, no backtrace |
| Python tree | `./run-tests` still green — step 12 must not touch it |

Two of these are new and deserve to exist: nothing currently exercises **compaction** or the
**token ceiling**, and both are step 12's whole point.

## 7. Risks

- **The `tasks.player` settings keys are load-bearing in both trees.** Step 12 reads them through
  different code but the same YAML. Any edit to `.boukensha/settings.yaml` must leave step 11 and
  the Python tree working — verify all three after Q2.
- **`max_turn_tokens: 60_000` is a live ceiling.** A long MUD session that previously ran to
  `max_iterations` may now stop earlier on spend. Expected, but it will look like a regression if
  it is not anticipated.
- **`compact_messages!` drops the oldest 40% outright** — no summarization. On a MUD session that
  discards the early exploration the agent may re-walk ground it already covered. Worth watching
  once real sessions run.

## 8. Notes

- Nothing here is committed until you say so.
- The `mud_manager` gem needs no changes; 0.2.3 is installed and step-independent.
- Effort once questions are answered: mostly mechanical. The two merges that need care are
  `config.rb` and `boukensha.rb`, because both mix step-12 content with our fixes in the same
  methods.
