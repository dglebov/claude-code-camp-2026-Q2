# Step 12 — Context Management: Python port

Reference: `week1_baseline/ruby/12_context/` (ours, carried forward and shipping)
Target:    `week1_baseline/python/12_context/`
Baseline:  `week1_baseline/python/11_tui/` (538 tests, green)

> **Status: awaiting review.** Five questions in §1 change what gets built. Answer them inline,
> then say execute.

---

## 1. Decisions

### Settled — do not re-litigate

| # | Decision | Why |
|---|---|---|
| D1 | Port targets `week1_baseline/python/12_context/`, a full copy of the step-11 package plus the new work | Every step ships a self-contained `boukensha`; established shape |
| D2 | The Ruby reference is **our** `12_context`, not upstream's | Upstream's lacks MCP, the config walk-up, `required_keys`, and ten other things; that work is already carried forward |
| D3 | Textual stays the TUI framework | Settled in step 11 |
| D4 | `--no-tui` and the non-TTY auto-fallback carry over unchanged | The suite and `verify-python` depend on them |

### Open — these block execution

#### Q1. Delete `boukensha/tasks/`? *(recommend: yes)*

Ruby step 12 deletes `Tasks::Base` / `Tasks::Player` and replaces the abstraction with direct
`Config` readers (`provider_type`, `model`, `system_prompt`, `agent_max_*`). The `tasks.player.*`
YAML keys survive; only the classes go.

Mirroring that in Python is a wider change than it looks:

| Site | Today | After |
|---|---|---|
| `Context.__init__` | `task` is a **required** keyword arg | removed |
| `Context.__repr__` | prints `task.task_name()` | drops it |
| `Agent._resolve_max_iterations` / `_resolve_max_output_tokens` | read `context.task` | read the passed-in values |
| `Agent._log_response` | passes `task=self._context.task` to the logger | drops it |
| `boukensha/tasks/` (3 files) | — | deleted |
| `tests/test_tasks.py` | **20 tests** | deleted |
| `Config.tasks()` | used by `run`/`repl` | replaced by the new readers |

**Recommendation: yes** — the trees have to stay diffable, and keeping the task classes on the
Python side would leave two config paths, exactly the objection that settled it for Ruby. Note the
suite drops from 538 to ~518 before the new step-12 tests are added.

#### Q2. Disable `list_directory` and `search_files`? *(recommend: yes)*

Ruby step 12 comments both out with a note — *"leftover from when this app was a coding harness;
the current player agent has no use for it"* — giving 5 built-ins and **39 tools** total. Python
currently registers all 6.

**Recommendation: match Ruby**, so the two trees advertise the same surface to the model, and say
plainly in the code why. This also touches `tests/test_tools_file_system.py`, which covers both.

#### Q3. `usage_pct` rounding — match Ruby explicitly? *(recommend: yes)*

`Context#usage_pct` is `(usage_fraction * 100).round`. **Ruby and Python round `.5` differently:**

```ruby
(0.5).round   # => 1     Ruby: half away from zero
```
```python
round(0.5)    # => 0     Python: banker's rounding, ties to even
```

So a context at exactly 70.5% shows `71%` in Ruby and `70%` in Python — and 70 vs 71 is the
threshold where the TUI turns yellow. Small, but it is a visible cross-tree divergence sitting
right on a boundary.

**Recommendation: implement half-up explicitly** (`math.floor(x + 0.5)` for non-negative values)
and comment why, rather than reaching for `round()` and inheriting a different rule.

#### Q4. Ship `prompts/` + a `PROMPTS_DIR` fallback? *(recommend: yes)*

Ruby step 12's `load_system_prompt` reads only the config directory; with no `.boukensha/prompts/`
it returned `nil` and the agent ran with **no system prompt at all**, silently. I fixed that in the
Ruby step by restoring `PROMPTS_DIR` and bundling `prompts/system.md`.

Python step 11 already has both (`Config.PROMPTS_DIR`, `prompts/system.md`). The port must keep
them wired into the *new* config path — dropping `Tasks::Base` is exactly what removed the fallback
on the Ruby side.

**Recommendation: keep the fallback, and add a test for it** — it failed silently once already.

#### Q5. Extend `verify-python` to cover step 12? *(recommend: yes, default it to 12)*

`verify-python` already takes a step argument and defaults to the newest. Bumping the default to
`12_context` keeps it testing the tip. Its 15 checks are all step-agnostic.

---

## 2. Reference files — what to port

### New

| Ruby | Lines | Python target |
|---|---|---|
| `lib/boukensha/models.rb` | 21 | `boukensha/models.py` |

### Changed

| Ruby | Change |
|---|---|
| `context.rb` | Token/window state and the compaction machinery |
| `agent.rb` | `max_turn_tokens`, `record_usage`, `compact_if_needed`, `log_reasoning`, `plan` |
| `backends/base.rb` + 5 backends | Normalized `"reasoning"` content block |
| `logger.rb` | `reasoning`, `plan`, `compaction`; `prompt(context_window:)`; `turn_end(tokens:)` |
| `config.rb` | `provider_type`, `model`, `system_prompt`, `system_override?`, `agent_*` |
| `repl.rb` | `/compact` |
| `tui.rb` | Context-usage readout, colour thresholds, `⚠` |
| `tools/file_system.rb` | Two tools disabled (Q2) |

### Deleted

`boukensha/tasks/` (Q1).

---

## 3. What step 12 actually adds

Two independent ceilings and one new signal:

1. **Window pressure** — `current_tokens` vs `context_window`, refreshed from each response's
   `input_tokens`. At `compaction_threshold` (0.85) the agent drops the oldest 40% of messages
   before the next call. This is about *fitting*.
2. **Spend** — `turn_tokens` accumulates input+output across a turn; at `max_turn_tokens` (60k)
   the agent stops starting iterations and makes one wind-down call. This is about *cost*, and it
   is a genuinely new kind of limit: step 11 could only count iterations.
3. **Reasoning** — a normalized content block so a model's thinking is a first-class logged step
   rather than being discarded.

The Ruby side is verified working: compaction dropped 4 of 10 messages at a forced threshold, and
the ceiling tripped at exactly `max_turn_tokens` with the wind-down call billed on top.

---

## 4. Target layout

```
week1_baseline/python/12_context/
├── README.md
├── conftest.py
├── boukensha/
│   ├── models.py            # NEW
│   ├── context.py           # + window/token state, compaction
│   ├── agent.py             # + max_turn_tokens, reasoning, plan
│   ├── config.py            # redesigned readers
│   ├── logger.py            # + 3 events
│   ├── repl.py              # + /compact
│   ├── tui.py               # + ctx readout
│   ├── backends/            # + reasoning blocks
│   ├── version.py           # 0.12.0
│   └── …                    # rest copied from step 11
├── examples/example.py
├── prompts/system.md
└── tests/
    ├── test_models.py       # NEW
    ├── test_context.py      # extended
    ├── test_agent.py        # extended
    └── …
```

Plus `week1_baseline/bin/python/12_context`.

---

## 5. Ruby → Python semantic gaps new to this step

### 5.1 Rounding at the threshold boundary

See Q3. `round()` is not `Ruby#round`. This is the only gap that produces a *different number* on
the two sides rather than different code.

### 5.2 `compact_messages!` → `compact_messages`

Ruby's bang marks the mutation; Python has no such convention and `context.py` already drops it
elsewhere (`clear_messages!` → `clear_messages`). Keep dropping it, consistently.

The arithmetic must port exactly:

```ruby
drop_count = [(@messages.size * 0.40).ceil, @messages.size - 2].min
drop_count = [drop_count, 0].max
```

`(x).ceil` → `math.ceil(x)`. Note `math.ceil` returns an int in Python 3, so no further coercion —
but `min`/`max` argument order is the thing to get right, not the ceiling.

### 5.3 `Integer(v)` / `Float(v)` in the config readers

Ruby's `Integer("60000")` raises on junk; Python's `int("60000")` does too, but `int(1.9)` silently
truncates where `Integer(1.9)` raises. The `agent_*` readers take YAML values, so a float in
`settings.yaml` is reachable. Decide once and comment: I'd use `int(v)` and accept truncation,
since YAML integers are the documented shape and raising on a float would be a new failure mode
Ruby users never see.

### 5.4 Reasoning blocks are provider-shaped

Each backend normalizes its own provider's response into
`{"type": "reasoning", "text":, "signature":, "redacted":}`. Anthropic's thinking blocks, OpenAI's
reasoning summaries and Ollama's absence of any all map differently — port each backend's mapping
from its Ruby counterpart rather than writing one generic transform.

`Agent.log_reasoning` skips empty non-redacted blocks; a redacted block still logs, because it
tells the reader "the model thought here". Preserve that asymmetry.

### 5.5 Colour thresholds in Textual

Ruby picks a lipgloss colour per render. Textual wants classes. `tui.py` already switches
`-active`/`-idle` via `set_classes`; extend the same mechanism with `-warn` (≥70%) and `-alert`
(≥85%) rather than building inline styles.

The `⚠` in the status bar is plain text — no styling needed.

### 5.6 `Context` loses a required argument

`Context(task=…)` is currently keyword-**required**, deliberately, so it fails like Ruby's. After
Q1 the signature becomes `Context(system=…, context_window=…, working_dir=…,
compaction_threshold=…)`. Every construction site in tests and `verify-python` must be updated —
this is the single largest mechanical change in the port.

---

## 6. Implementation steps

| # | Task |
|---|---|
| 1 | Copy `python/11_tui/` → `python/12_context/`; bump `version.py` to `0.12.0`; drop `__pycache__` |
| 2 | `boukensha/models.py` + `tests/test_models.py` |
| 3 | `context.py`: window/token state, compaction, `usage_pct` (Q3); remove `task` (Q1) |
| 4 | `config.py`: new readers; keep the walk-up, `mcp_servers`, and the `PROMPTS_DIR` fallback (Q4) |
| 5 | Delete `boukensha/tasks/` and `tests/test_tasks.py` (Q1); fix every `Context(...)` call site |
| 6 | `logger.py`: `reasoning`, `plan`, `compaction`; `prompt(context_window=)`; `turn_end(tokens=)` |
| 7 | `backends/`: reasoning normalization in all five + the contract docstring in `base.py` |
| 8 | `agent.py`: `max_turn_tokens`, `_token_limit_reached`, `_record_usage`, `_compact_if_needed`, `_log_reasoning`, plan logging |
| 9 | `repl.py`: `/compact` in `handle_command`, `HELP`, and the banner |
| 10 | `tui.py`: ctx readout + threshold classes (§5.5) |
| 11 | `tools/file_system.py`: disable two tools (Q2) |
| 12 | `bin/python/12_context` launcher; bump `verify-python`'s default (Q5) |
| 13 | `README.md` for the step |

---

## 7. Verification

### 7.1 Offline suite

`./run-tests` from `week1_baseline/python`. Expect roughly 518 carried (538 − 20 task tests) plus
the new ones. **No step-12 test may launch a full-screen app** — same rule as step 11.

New tests, at minimum:

- `Models.context_window` for a known id, an unknown id (32k default), and a `None`/empty id
- `usage_fraction` / `usage_pct` including the `.5` boundary (Q3) and a zero-width guard
- `needs_compaction` at, just below, and just above the threshold
- `compact_messages` drop arithmetic: the 40% rule, the "keep at least 2" floor, and a 0/1/2-message
  context where the floor and the ceiling fight
- `update_tokens` / `reset_turn_tokens` / `add_turn_tokens`
- Agent: the token ceiling trips and winds down exactly once; `turn_tokens` includes the wind-down
- Agent: compaction fires before the next call and emits a `compaction` event
- Agent: `_log_reasoning` skips empty non-redacted blocks, keeps redacted ones
- Backends: each emits a reasoning block from its provider's shape
- `/compact` returns `"command"` and reports the drop count

### 7.2 Parity with Ruby

- `--no-tui` transcript byte-identical to Ruby's (banner now carries `step:` and `/compact`)
- Same tool count and names (39, if Q2)
- `Models::TABLE` keys identical

### 7.3 MCP

`week1_baseline/mcp/verify-python` (15 checks) against step 12.

### 7.4 TUI

Headless pilot for boot/turn/exit as in step 11, plus a pty run asserting the `ctx N/M (P%)`
readout renders. **A pilot test that drives the real app is worth writing again** — it is what
caught the `App._context` collision last time.

---

## 8. Known drift in the Ruby step-12 reference

Fixed while preparing this plan, and worth knowing because the port inherits the corrected form:

- All five Ruby backends still built tool schemas with `tool.parameters.keys`, so the
  `Tool#required_keys` carried forward in the step-12 work was **inert** — MCP's optional
  parameters (e.g. `look`'s `target`) were being advertised to the model as mandatory. Now
  `required_keys` in all five; verified `move` → `["direction"]`, `look` → `[]`.
- `anthropic.rb` in step 12 also drops the `claude-haiku-4-5-20251001` dated entry that step 11
  carried. Port the table as step 12 has it.

## 9. Notes

- Nothing is committed. Ruby step 12 is staged but uncommitted from the previous task.
- The MUD on `localhost:4000` is currently **down**, so any live end-to-end check needs
  `docker compose up -d` from `week0_explore/infrastructure` first. The offline suite and
  `verify-python` (stub MUD) do not need it.
- Effort: larger than step 11's port. The mechanical bulk is Q1's ripple through every `Context(...)`
  call site; the fiddly parts are the five backends' reasoning mappings and the compaction
  arithmetic edge cases.
