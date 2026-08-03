# Plan — Make Every Ruby Step Runnable, and Keep It That Way

**Scope:** the `week1_baseline/ruby` tree and `week1_baseline/bin/ruby`. No Python changes.

**Why now:** the same two-line path regression has appeared in **six consecutive steps**. It has
been patched five times, once per port. Step 06 has it again, and also ships without a launcher.

---

## 1. Current state (audited 2026-08-03)

| Step | Launcher | `BOUKENSHA_DIR` (example.rb) | `PROMPTS_DIR` (config.rb) | Runs? |
|---|---|---|---|---|
| `00_config` | yes | OK | OK | ✅ |
| `01_struct_skeleton` | yes | OK | *(none)* | ✅ |
| `02_the_registry` | yes | OK | *(none)* | ✅ |
| `03_prompt_builder` | yes | OK | OK | ✅ |
| `04_api_client` | yes | OK | OK | ✅ (fixed 2026-08-03) |
| `05_agent_loop` | yes | OK | OK | ✅ (fixed 2026-08-03) |
| `06_the_logger` | **MISSING** | **BROKEN** → `week1_baseline/.boukensha` | **BROKEN** → `week1_baseline/ruby/prompts` | ❌ |

00–03 verified by execution (they are offline and free). 04–05 verified by live run. **Only step
06 is broken.**

---

## 2. The recurring bug

Two constants, each a hand-typed count of `..` segments, retyped on every copy-forward:

| Constant | Lives in | Correct depth | Why |
|---|---|---|---|
| `BOUKENSHA_DIR` | `examples/example.rb:1` | **4** — `../../../../.boukensha` | `examples/` → step → `ruby/` → `week1_baseline/` → repo root |
| `PROMPTS_DIR` | `lib/boukensha/config.rb:13` | **2** — `../../prompts` | `lib/boukensha/` → `lib/` → step root |

Both depths are **constant across every step**. Neither has ever legitimately needed to change.
Every occurrence has been a copy-forward that adjusted the count when it should have left it alone.

**Both fail silently in the same shape:** the path resolves to a directory that does not exist,
`Config` reads nothing, and the failure surfaces far from its cause — `BOUKENSHA_DIR` as
`ArgumentError: tasks.player.provider is required in settings.yaml`, and `PROMPTS_DIR` as a
`400 — "system: Input should be a valid array"` from the provider, which reads convincingly like
an auth or payload problem. Neither error names a path.

---

## 3. Immediate fixes (step 06)

**3.1 — `BOUKENSHA_DIR`.**

```diff
-ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../.boukensha", __dir__)
+ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../../.boukensha", __dir__)
```

**3.2 — `PROMPTS_DIR`.**

```diff
-    PROMPTS_DIR = File.expand_path("../../../prompts", __dir__).freeze
+    PROMPTS_DIR = File.expand_path("../../prompts", __dir__).freeze
```

**3.3 — the missing launcher**, `week1_baseline/bin/ruby/06_the_logger`, mode `755`:

```bash
#!/usr/bin/env bash

cd "$(dirname "$0")/../../ruby/06_the_logger"
bundle exec ruby examples/example.rb
```

**3.4 — `bin/ruby/04_api_client` had mode `744`** where every other launcher is `755`. Already
corrected; noted here so the audit is complete.

---

## 4. Stopping the recurrence

A systemic fix was declined once (see `05_agent_loop.md` §9.3) on the grounds that it would
disturb the Ruby/Python mirroring. That reasoning still holds for changing *how* paths resolve —
but not for **checking** them, which is purely additive.

### Recommended: a path guard (additive, no behaviour change)

`week1_baseline/bin/ruby/check-paths` — walks every step and asserts both constants resolve to
directories that exist. Zero API calls, runs in well under a second, and changes no library code,
so the two trees stay byte-comparable.

```bash
#!/usr/bin/env bash
# Asserts every Ruby step's path constants resolve to real directories.
# The depths are invariant: 4 from examples/ to the repo root, 2 from lib/boukensha/ to the step.
set -uo pipefail
cd "$(dirname "$0")/../../ruby"

failed=0
for step in */; do
  step=${step%/}

  example="$step/examples/example.rb"
  if [ -f "$example" ]; then
    raw=$(grep -m1 -o 'File.expand_path("[^"]*\.boukensha"' "$example" | sed 's/.*"\(.*\)"/\1/')
    dir=$(ruby -e "puts File.expand_path('$raw', '$PWD/$step/examples')")
    if [ ! -d "$dir" ]; then
      echo "FAIL $step  BOUKENSHA_DIR -> $dir (does not exist)"; failed=1
    fi
  fi

  config="$step/lib/boukensha/config.rb"
  if [ -f "$config" ] && grep -q PROMPTS_DIR "$config"; then
    raw=$(grep -m1 -o 'File.expand_path("[^"]*prompts"' "$config" | sed 's/.*"\(.*\)"/\1/')
    dir=$(ruby -e "puts File.expand_path('$raw', '$PWD/$step/lib/boukensha')")
    if [ ! -d "$dir" ]; then
      echo "FAIL $step  PROMPTS_DIR -> $dir (does not exist)"; failed=1
    fi
  fi

  if [ ! -x "../bin/ruby/$step" ]; then
    echo "FAIL $step  launcher missing or not executable: bin/ruby/$step"; failed=1
  fi
done

[ "$failed" -eq 0 ] && echo "All Ruby steps: paths resolve, launchers present."
exit "$failed"
```

Run it after every copy-forward, and as the first step of any future port plan's §9.

### Considered and not recommended (for now)

| Option | Why not |
|---|---|
| Resolve `.boukensha` by walking **up** until found | Removes the arithmetic entirely and is the real fix — but it changes `Config`, which the Python tree mirrors line for line across six steps. That is a six-step, two-language change in service of a bug the guard already catches. Revisit if the guard ever fires twice. |
| Derive `PROMPTS_DIR` from `__dir__` + a marker file | Same objection, smaller blast radius. |
| A Ruby spec instead of a shell script | The Ruby steps ship no spec suite at all — steps 04, 05 and 06 have no tests of any kind. Adding a test framework to host one assertion is disproportionate. |

---

## 5. Verification

```bash
# 1. The guard passes
./week1_baseline/bin/ruby/check-paths

# 2. The offline steps still run (free)
for s in 00_config 01_struct_skeleton 02_the_registry 03_prompt_builder; do
  ./week1_baseline/bin/ruby/$s >/dev/null && echo "$s OK"
done

# 3. Step 06 runs end to end (billed — several calls)
./week1_baseline/bin/ruby/06_the_logger

# 4. And writes its log
ls -la .boukensha/sessions/
```

Steps 04 and 05 are known-good as of 2026-08-03 and need no re-run unless the guard flags them.

---

## 6. Found during execution — session logs were not gitignored

Running step 06 creates `.boukensha/sessions/<id>.jsonl`, and nothing ignored it. Each line's
`messages` key carries the **full conversation**, including the contents of every file the agent's
tools read — so the logs are both noisy in diffs and potentially sensitive. Added to `.gitignore`:

```
.boukensha/sessions/
```

Not anticipated by this plan; recorded because the directory only comes into existence the first
time step 06 runs, which is easy to do without noticing what landed in the working tree.

---

## 7. Notes

- **Do not "fix" step 06's `config.rb` beyond the path.** It also drops the four `mud_*` readers
  present in step 05. That looks like a deliberate removal (nothing references them), not a
  regression — leave it, and record it in the port plan's drift section.
- The guard checks launchers too, because step 06 shipped without one and nothing caught it.
- If a future step legitimately changes directory depth, the guard fails loudly and the fix is to
  update the guard's expectations — which is the point: the depth becomes an explicit decision
  rather than a silently retyped literal.
