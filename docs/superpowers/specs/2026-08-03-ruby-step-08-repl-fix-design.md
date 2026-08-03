# Design — Fix `week1_baseline/ruby/08_the_repl_loop`

Date: 2026-08-03

## Problem

Step 08 was copy-forwarded from step 07 and shipped with the retyped-path-depth
regression that `bin/ruby/check-paths` was written to catch. The step is currently
unrunnable, and the README describes a directory that does not exist.

`bin/ruby/check-paths` reports three failures for `08_the_repl_loop`; steps 00–07 pass.

```
FAIL 08_the_repl_loop  BOUKENSHA_DIR -> week1_baseline/.boukensha   (does not exist)
FAIL 08_the_repl_loop  PROMPTS_DIR   -> week1_baseline/ruby/prompts (does not exist)
FAIL 08_the_repl_loop  launcher missing or not executable: bin/ruby/08_the_repl_loop
```

Observed symptoms, both of which name something other than a path:

- **`BOUKENSHA_DIR`** — loud. `ruby examples/example.rb` aborts with
  `tasks.player.model is required in settings.yaml`, because the resolved config
  directory does not exist and so carries no `settings.yaml`.
- **`PROMPTS_DIR`** — silent. `Tasks::Player.system_prompt(...)` returns `nil`
  (verified directly). Nothing complains locally; it surfaces later as a 400 from
  the provider about `system` on the first real turn.

A separate copy-forward slip shifted the README step numbers: `07_the_run_dsl`
titles itself "Step 6", and `08_the_repl_loop` inherited the shift and titles
itself "Step 7".

## Non-goals

- No Python port of step 08. That is a new port, not a fix.
- No review or change of REPL logic. `repl.rb`, `agent.rb`, and `context.rb` are
  not touched. With `BOUKENSHA_DIR` corrected by hand the REPL already boots,
  renders its banner, and handles `/help` and `/exit` correctly.
- No renumbering of steps 00–05, which use bare titles with no step number.

## Approach

Restore the two constants to the depths every other step uses, rather than making
them self-locating (walking up for a marker directory).

`check-paths` already encodes those depths as invariants — "`BOUKENSHA_DIR` 4 levels
from `examples/`", "`PROMPTS_DIR` 2 levels from `lib/boukensha/`" — so matching them
keeps the checker as the single source of truth. Self-locating paths would end the
bug class permanently, but they would make step 08's `config.rb` structurally
different from steps 00–07. In a teaching repo where each step is a readable
snapshot of the one before, that divergence costs more than it saves, and it does
nothing for the steps already shipped.

## Changes

### 1. `ruby/08_the_repl_loop/examples/example.rb:1` — config directory depth

`"../../../.boukensha"` → `"../../../../.boukensha"`

Resolves to the repo-root `.boukensha`, which exists and holds `settings.yaml`.
Matches step 07.

### 2. `ruby/08_the_repl_loop/lib/boukensha/config.rb:13` — prompts directory depth

`"../../../prompts"` → `"../../prompts"`

Resolves to `08_the_repl_loop/prompts/`, which already ships `system.md`.
Matches steps 00–07.

### 3. `bin/ruby/08_the_repl_loop` — new launcher

Modelled verbatim on `bin/ruby/07_the_run_dsl`:

```bash
#!/usr/bin/env bash

cd "$(dirname "$0")/../../ruby/08_the_repl_loop"
bundle exec ruby examples/example.rb
```

Mode `755`, matching every other launcher. `bundle exec` is already confirmed
working in the step directory, and its `Gemfile`/`Gemfile.lock` are byte-identical
to step 07's, so no gem setup is needed.

### 4. `ruby/08_the_repl_loop/README.md` — renumber and correct the run instructions

Renumber so the title matches the directory, and shift every reference to the
previous step by one:

| Line | Current | Corrected |
|---|---|---|
| 1 | `# Step 7 — The REPL Loop` | `# Step 8 — The REPL Loop` |
| 5 | `\| \| Step 6 \| Step 7 \|` | `\| \| Step 7 \| Step 8 \|` |
| 43 | `## Changes from step 6` | `## Changes from step 7` |
| 49 | `Before step 7, the agent…` | `Before step 8, the agent…` |
| 54 | `# step 6 — final text returned…` | `# step 7 — final text returned…` |
| 57 | `# step 7 — final text added…` | `# step 8 — final text added…` |

And the "Running it" block, which currently names two paths that do not exist:

```
cd 07_the_repl_loop
ANTHROPIC_API_KEY=your_key ruby examples/step7.rb
```

becomes the actual invocation:

```
cd 08_the_repl_loop
ANTHROPIC_API_KEY=your_key bundle exec ruby examples/example.rb
```

with a note that `bin/ruby/08_the_repl_loop` runs it from anywhere, matching how
`week1_baseline/python/README.md` documents its launchers.

### 5. `ruby/08_the_repl_loop/examples/example.rb:12` — sandbox base directory

`File.expand_path("../../07_the_run_dsl", __dir__)` →
`File.expand_path("..", __dir__)`

Step 08's REPL currently browses step 07's source. Step 07's own example uses
`File.expand_path("..", __dir__)` — the step's own root — so this is the same
copy-forward leftover. The accompanying comment ("the step 7 folder makes a good
playground") is updated to match.

### 6. `ruby/07_the_run_dsl/README.md:1` — the inherited off-by-one

`# Step 6 — The Boukensha.run DSL` → `# Step 7 — The Boukensha.run DSL`

This is the only change outside step 08. It is included because it is the source
of step 08's shift — fixing 08 alone would leave two adjacent READMEs both
claiming to be about the run DSL and the logger at the wrong numbers. It is one
line and can be dropped without affecting anything else in this spec.

## Verification

Each check maps to a specific failure above.

1. `week1_baseline/bin/ruby/check-paths` exits 0 with
   `All Ruby steps: paths resolve, launchers present.` — covers changes 1–3.
2. `printf '/help\n/exit\n' | week1_baseline/bin/ruby/08_the_repl_loop` — banner
   renders, help prints, exits on "Goodbye.". Requires no API key and makes no API
   call. Covers change 3 end-to-end.
3. `Tasks::Player.system_prompt(...)` returns the contents of `prompts/system.md`
   rather than `nil`. Covers change 2, which check-paths catches by path but which
   is otherwise invisible in the smoke test — it would only surface as a provider
   400 on a real turn.
4. No stale references remain in step 08: grep for `step7`, `07_the_repl_loop`,
   and `Step 6` under `ruby/08_the_repl_loop/` returns nothing.
5. The step-numbering audit reports `ok` for 06, 07, and 08 — covers changes 4 and 6.

## Delivery

`week1_baseline/ruby/08_the_repl_loop/` is currently untracked — the step has never
been committed. The implementation commit therefore adds the whole directory
alongside the fixes, so step 08 enters git already correct rather than as a broken
commit followed by a repair commit.

## Risk

Low. Five of the six changes are path literals, documentation text, and one new
three-line shell script. No library logic is modified, so the REPL's runtime
behaviour is unchanged apart from now finding its config and system prompt.

The Ruby steps ship no test suite, so `check-paths` plus the scripted REPL smoke
run are the available regression evidence.
