# Plan — Make `ruby/09_global_executable` Runnable

**Scope:** `week1_baseline/ruby/09_global_executable`, plus one launcher in `week1_baseline/bin/ruby`
and one guard extension in `bin/ruby/check-paths`. No Python changes.

**Status:** plan only. Nothing has been edited. Awaiting review.

**Why now:** step 09 is untracked, does not run from the repo, and ships the same path regression
for the **ninth** consecutive step — this time in a shape `check-paths` cannot fully see.

---

## 1. Current state (audited 2026-08-03)

`bin/ruby/check-paths` reports two failures; three more defects sit outside its reach.

```
FAIL 09_global_executable  PROMPTS_DIR -> week1_baseline/ruby/prompts (does not exist)
FAIL 09_global_executable  launcher missing or not executable: bin/ruby/09_global_executable
```

| # | Defect | Symptom observed | Caught by |
|---|---|---|---|
| 1 | `PROMPTS_DIR` is `../../../prompts` | `system_prompt` resolves to **nil** — verified directly | check-paths |
| 2 | No `bin/ruby/09_global_executable` launcher | step unreachable from the repo root | check-paths |
| 3 | `bin/boukensha` is mode **644**, not executable | a "global executable" that cannot be executed | nothing |
| 4 | Nothing sets `BOUKENSHA_DIR`, and the cwd tier was dropped (§3.2) | `tasks.player.model is required in settings.yaml` | nothing |
| 5 | `gemspec` omits `prompts/`, and `PROMPTS_DIR` points outside the gem | an installed gem has no system prompt at all | nothing |

Reproduction of #4, the loud one:

```
$ printf '/help\n/exit\n' | ruby bin/boukensha
lib/boukensha/tasks/base.rb:16:in 'model': tasks.player.model is required in settings.yaml (ArgumentError)
```

With `BOUKENSHA_DIR` pointed at the repo-root `.boukensha` by hand, the step runs correctly —
banner, `/help`, `/exit`, clean exit. **The REPL and loader logic are sound.** Everything below
is paths, permissions, packaging, and prose.

---

## 2. The recurring bug, and the guard's blind spot

`PROMPTS_DIR` is wrong for the ninth step running. The guard caught it, as designed.

What the guard **missed** is #4. `check-paths` only checks `BOUKENSHA_DIR` when
`$step/examples/example.rb` exists:

```bash
example="$step/examples/example.rb"
if [ -f "$example" ]; then
  raw=$(grep -m1 -o 'File.expand_path("[^"]*\.boukensha"' "$example" | ...)
```

Step 09 is the first step with **no `examples/` directory** — its entry point is `bin/boukensha`.
So the config-directory check silently skipped, and the failure surfaced as the same misleading
`settings.yaml` message the guard was built to prevent. A guard that silently skips is worse than
one that fails: the green line reads as "checked and fine".

Extending the guard is §4.5.

---

## 3. Three step-08 features are missing in step 09 — **decisions needed**

These are not obviously bugs. Each was added deliberately in step 08 and is absent in step 09,
and step 09's `config.rb` is *not* a copy of step 07's either, so this was hand-edited rather
than mis-copied wholesale. I am not guessing at intent — please rule on each.

### 3.1 The 401 error message was removed

Step 08 added, and step 09 deletes:

```ruby
if response.code.to_i == 401
  raise ApiError, "authentication failed (401) — check your API key"
end
```

A globally installed binary is *more* likely to be run without a key than an in-repo example, so
this reads like an accidental revert. **Decision: restore, or accept the removal?**

### 3.2 The cwd `.boukensha` tier was removed

Step 08's three-tier `resolve_dir` (env var → `./.boukensha` → `~/.boukensha`) is back to two
tiers in step 09. This is the direct cause of defect #4: with no `examples/example.rb` to set
`BOUKENSHA_DIR` and no cwd tier, running from the repo finds nothing (`~/.boukensha` does not
exist on this machine).

This one has an argument on both sides. A global command arguably *should* use one home config
rather than picking up whatever directory you happen to be standing in — but that is exactly the
behaviour that makes step 09 unrunnable from the repo without an env var.

**Decision: restore the cwd tier, or keep two tiers and have the launcher set `BOUKENSHA_DIR`?**
This choice determines §4.4. My recommendation is to keep the two-tier resolution (a global tool
with a predictable config location is the more defensible design) and have the repo launcher
export `BOUKENSHA_DIR` explicitly, matching what every other step's `example.rb` already does.

### 3.3 The banner dropped its two status indicators

Step 08 showed `✓ API key set` / `✗ API key not set` and flagged a missing config directory.
Step 09's banner replaces both with plain `config:` / `provider:` / `model:` lines. This one looks
**intentional** — the layout was genuinely reworked, not just deleted. Flagging for completeness;
no action proposed unless you disagree.

---

## 4. Fixes

### 4.1 `lib/boukensha/config.rb:13` — the path constant

```ruby
PROMPTS_DIR = File.expand_path("../../prompts", __dir__).freeze
```

Two levels up from `lib/boukensha/`, matching steps 00–08. Currently three.

### 4.2 `bin/boukensha` — make it executable

```bash
chmod 755 week1_baseline/ruby/09_global_executable/bin/boukensha
```

Git records this as a mode change, so it survives clone. Every other launcher in the repo is 755.

### 4.3 `boukensha.gemspec` — ship the prompts

```ruby
spec.files = Dir["lib/**/*.rb"] + Dir["prompts/**/*"] + ["bin/boukensha", "README.md"]
```

Currently 24 files, none of them `prompts/system.md`. Combined with §4.1, an installed gem then
carries its own default system prompt and `PROMPTS_DIR` resolves inside the gem — which is the
whole point of a self-contained global executable.

Worth confirming after the change: `gem build` then inspect `spec.files` for `prompts/system.md`.

### 4.4 `bin/ruby/09_global_executable` — the repo launcher

Shape depends on the §3.2 ruling. Under my recommendation (keep two tiers):

```bash
#!/usr/bin/env bash

cd "$(dirname "$0")/../../ruby/09_global_executable"
export BOUKENSHA_DIR="${BOUKENSHA_DIR:-$(cd ../../.. && pwd)/.boukensha}"
bundle exec ruby bin/boukensha
```

`${BOUKENSHA_DIR:-…}` mirrors the `||=` every `example.rb` uses, so an explicitly set value still
wins. Mode 755.

If you instead restore the cwd tier (§3.2), the `export` line comes out and the `cd` target
becomes the repo root.

### 4.5 `bin/ruby/check-paths` — close the blind spot

Two changes, both additive:

1. When a step has **no** `examples/example.rb`, do not silently skip the config-directory check —
   assert instead that the step's launcher sets `BOUKENSHA_DIR`, and report a distinct
   `SKIPPED`/`FAIL` line rather than nothing.
2. Assert that any `bin/` entry point inside a step directory is executable — the check that would
   have caught #3.

Without this, the next step in this shape reproduces both failures with a green guard.

### 4.6 Documentation

`README.md` step numbers are off by one throughout, and several paths do not exist:

| Line | Current | Corrected |
|---|---|---|
| 1 | `# Step 8 — Global Executable` | `# Step 9 — Global Executable` |
| 10 | `step 7's lib, bundled as the default` | `step 8's lib, bundled as the default` |
| 15 | `cd 08_global_executable` | `cd 09_global_executable` |
| 17 | `gem install boukensha-0.1.0.gem` | `gem install boukensha-0.9.0.gem` (VERSION is `0.9.0`) |
| 28-29, 37-38 | `07_the_repl_loop` | `08_the_repl_loop` |
| 40-43 | `06_the_run_dsl` (no such directory) | `07_the_run_dsl` |

`lib/boukensha_loader.rb` carries the same drift in its comments and in two `abort` messages
users will actually see:

| Line | Current | Corrected |
|---|---|---|
| 6 | `bundled inside this gem (step 8 — …)` | `(step 8's lib — …)`, or drop the number |
| 31 | `BOUKENSHA_PATH=~/Sites/boukensha/07_the_repl_loop` | `08_the_repl_loop` |
| 66 | `does not support the interactive REPL (added in step 7)` | `(added in step 8)` |
| 69 | `Or point BOUKENSHA_PATH at step 7 or later` | `step 8 or later` |

Also add a **Run from the repo** section naming `./week1_baseline/bin/ruby/09_global_executable`,
which the README currently has no equivalent of — it documents `gem install` only.

---

## 5. Verification

All offline. No API call, no key, no `gem install` into the user's system gems.

```bash
# 1. The guard, now including the extended checks
week1_baseline/bin/ruby/check-paths

# 2. The step runs from the repo
printf '/help\n/exit\n' | ./week1_baseline/bin/ruby/09_global_executable

# 3. The silent one: the system prompt is no longer nil
cd week1_baseline/ruby/09_global_executable
BOUKENSHA_DIR="$(cd ../../.. && pwd)/.boukensha" ruby -Ilib -e '
  require "boukensha"
  cfg = Boukensha.config
  sp = Boukensha::Tasks::Player.system_prompt(cfg.tasks("player"),
         user_prompts_dir: cfg.user_prompts_dir,
         default_prompts_dir: Boukensha::Config::PROMPTS_DIR)
  raise "system prompt is nil" if sp.nil? || sp.strip.empty?
  puts "system prompt OK (#{sp.length} chars)"'

# 4. The gem packages its prompts
gem build boukensha.gemspec && \
  ruby -e 'puts Gem::Specification.load("boukensha.gemspec").files.grep(/prompts/)'

# 5. The loader's step selection still works
BOUKENSHA_PATH=../08_the_repl_loop BOUKENSHA_DEBUG=1 \
  bash -c "printf '/exit\n' | ruby bin/boukensha"     # loads step 08, prints the debug line
BOUKENSHA_PATH=/nonexistent ruby bin/boukensha        # aborts with the guidance message

# 6. No stale references survive
grep -rn 'Step 8\|07_the_repl_loop\|06_the_run_dsl\|0\.1\.0' \
  week1_baseline/ruby/09_global_executable/
```

Expected: (1) `All Ruby steps: paths resolve, launchers present.`; (2) banner, command list,
`Goodbye.`; (3) non-zero character count; (4) `prompts/system.md` listed; (5) debug line names
`08_the_repl_loop`, and the bad path aborts cleanly rather than raising; (6) no output.

Delete the built `.gem` afterwards, or add `*.gem` to `.gitignore` — worth checking which,
since the step is about to enter git for the first time.

---

## 6. Delivery

`week1_baseline/ruby/09_global_executable/` is untracked. As with step 08, it should enter git
already fixed rather than as a broken commit plus a repair commit.

**Commits are yours to make.** I will leave everything staged-but-uncommitted and report the
working tree.

---

## 7. Notes

- The pattern from `ruby_runnability.md` §2 holds: both surviving path defects are **silent and
  misleading**. A wrong `PROMPTS_DIR` reads as a provider 400 about `system`; a missing config
  directory reads as `tasks.player.model is required in settings.yaml`. Neither names a path.
  Step 09 adds a third to the family — an un-executable executable, which reads as
  `permission denied` from a shell, far from the gemspec that should have set the bit.
- §2 is the more important half of this plan. The guard did its job on the defect it covers, and
  its silent skip on the defect it does not cover is exactly how the ninth occurrence got here.
  Step 09 changes the *shape* of a step for the first time since step 00; the guard's assumptions
  need to change with it.
- §3 is the only place where I am guessing at intent, which is why nothing there is proposed as a
  fix. Two features that a global binary would plausibly want — a key-specific error message and a
  project-local config — are absent, and the third change is clearly deliberate. If §3.1 and §3.2
  were accidental, they are worth catching now; step 10 would inherit both.
- Ruby steps ship no test suite, so `check-paths` plus the scripted REPL run in §5 are the whole
  regression net. That is the argument for §4.5 being part of this change rather than a follow-up.
