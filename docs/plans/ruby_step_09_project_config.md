# Plan — Resolve config from the project directory, not the user's home

**Scope:** `week1_baseline/ruby/09_global_executable/lib/boukensha/config.rb`, plus two follow-on
adjustments this forces (`bin/ruby/09_global_executable` and `bin/ruby/check-paths`).

**Status:** plan only. Nothing edited. Awaiting review.

**Requirement:** running `boukensha` inside a project must use that project's `.boukensha`
directory, not `~/.boukensha`.

---

## 1. Why it currently reads from home

Step 09's resolution has two tiers and never looks at the project:

```ruby
def resolve_dir
  raw = ENV.fetch("BOUKENSHA_DIR", nil) || DEFAULT_DIR   # env var, else ~/.boukensha
  Pathname.new(raw).expand_path.to_s
end
```

Step 08 had a middle tier that step 09 dropped (`ruby_step_09_runnable.md` §3.2). This is also why
the installed command needed a `~/.boukensha` symlink to work at all.

---

## 2. The choice: cwd-only vs walk-up

Step 08's middle tier checked **only the exact working directory**:

```ruby
cwd_dir = Pathname.new(Dir.pwd).join(".boukensha")
return cwd_dir.to_s if cwd_dir.directory?
```

That satisfies "config from the project directory" only when you are standing in the project
**root**. `cd myproject/src && boukensha` misses `myproject/.boukensha` and silently falls back to
home — the same class of silent-wrong-config failure this repo keeps hitting.

**Recommendation: walk up from the working directory to the filesystem root**, taking the first
`.boukensha` directory found. This is how `git` finds `.git`, and how project-scoped tools locate
their config generally. It is a deliberate improvement over step 08, not a restoration, so the two
trees diverge by this method — worth noting since the step-08 Python port mirrors the three-tier
version.

Alternative if you want strict step-08 parity: use the cwd-only form and accept that it only works
from the project root. Everything else in this plan is unchanged either way.

---

## 3. Changes

### 3.1 `lib/boukensha/config.rb` — the resolution

```ruby
    # The .boukensha config directory is resolved in this order:
    #   1. BOUKENSHA_DIR environment variable (set before loading .env)
    #   2. The nearest .boukensha directory at or above the working directory
    #   3. ~/.boukensha  (default)
    DEFAULT_DIR = File.join(Dir.home, ".boukensha").freeze
```

```ruby
    def resolve_dir
      # 1. Explicit override
      return Pathname.new(ENV["BOUKENSHA_DIR"]).expand_path.to_s if ENV["BOUKENSHA_DIR"]

      # 2. The nearest .boukensha at or above the working directory. Walking up rather than
      #    checking only Dir.pwd (step 08's form) means `boukensha` works from anywhere inside a
      #    project, not just its root — a global command is usually run from a subdirectory.
      project_dir = find_project_dir(Pathname.new(Dir.pwd).expand_path)
      return project_dir.to_s if project_dir

      # 3. ~/.boukensha default
      Pathname.new(DEFAULT_DIR).expand_path.to_s
    end

    # Ascends to the filesystem root. `parent` of "/" is "/", so compare before and after to
    # terminate — an unconditional loop here hangs the process.
    def find_project_dir(start)
      dir = start
      loop do
        candidate = dir.join(".boukensha")
        return candidate if candidate.directory?

        parent = dir.parent
        return nil if parent == dir

        dir = parent
      end
    end
```

`find_project_dir` goes in the existing `private` section alongside `resolve_dir`.

**Edge case to be deliberate about:** with `~/.boukensha` present as a real directory (or the
symlink currently there), the walk-up finds it as soon as the cwd is anywhere under `$HOME` —
including `/Users/dglebov` itself. That is the same directory tier 3 would have returned, so the
result is identical; it just arrives one tier earlier. No behavioural difference, but it means the
walk-up effectively never reaches tier 3 for a user whose home holds a `.boukensha`.

### 3.2 `bin/ruby/09_global_executable` — stop overriding the new behaviour

The launcher currently exports `BOUKENSHA_DIR`, which is tier 1 and therefore **wins over project
detection**. With §3.1 in place the export is not just redundant, it actively defeats the feature
being added — the launcher `cd`s into the step directory, whose walk-up reaches the repo root
`.boukensha` on its own.

```bash
#!/usr/bin/env bash

cd "$(dirname "$0")/../../ruby/09_global_executable"
bundle exec ruby bin/boukensha
```

Verify the walk-up actually reaches it: from `week1_baseline/ruby/09_global_executable`, the
ancestors are `…/ruby`, `…/week1_baseline`, then the repo root, which holds `.boukensha`. Three
levels, terminating well before `$HOME`.

### 3.3 `bin/ruby/check-paths` — relax the assertion §3.2 breaks

The guard added yesterday asserts that a step with no `examples/` has a launcher setting
`BOUKENSHA_DIR`:

```bash
if [ -f "$launcher" ] && ! grep -qE '^[[:space:]]*(export[[:space:]]+)?BOUKENSHA_DIR=' "$launcher"; then
  echo "FAIL $step  no examples/ and bin/ruby/$step never sets BOUKENSHA_DIR"
```

Removing the export in §3.2 makes this fail. The assertion's *purpose* — "something must point
this step at a real config directory" — is still right; what satisfies it has changed. Replace the
grep with a behavioural check: run the launcher with `/exit` piped in and confirm it does not die
with the `settings.yaml` error.

```bash
    # No examples/ dir — the step's entry point is elsewhere (step 09 ships bin/boukensha).
    # Assert behaviourally that it finds a config directory, rather than assuming the mechanism:
    # step 09 resolves one by walking up from the working directory, with no env var involved.
    launcher="../bin/ruby/$step"
    if [ -x "$launcher" ]; then
      if printf '/exit\n' | "$launcher" 2>&1 | grep -q 'is required in settings.yaml'; then
        echo "FAIL $step  launcher runs but resolves no config directory"
        failed=1
      fi
    fi
```

This is strictly stronger than the grep — it catches a launcher that sets the variable to a path
that does not exist, which the grep would have passed. It costs one process spawn per such step
and still makes no API call, since `/exit` is handled before the agent runs.

### 3.4 Remove the `~/.boukensha` symlink

Created yesterday only because the installed command had no way to find project config. With
§3.1 that reason is gone.

```bash
rm ~/.boukensha
```

Keep it only if you want `boukensha` to still work outside any project. Worth an explicit
decision: with the symlink gone, running `boukensha` from, say, `/tmp` exits with
`tasks.player.model is required in settings.yaml` rather than falling back to anything.

### 3.5 README

The step README's "Install globally" section documents the `ln -s` workaround as the way to point
the installed command at this repo. Replace with the project-directory behaviour: `cd` into any
project containing `.boukensha` and run `boukensha`. Keep `BOUKENSHA_DIR` documented as the
explicit override.

---

## 4. Verification

```bash
# 1. The guard, with its new behavioural check
week1_baseline/bin/ruby/check-paths

# 2. From the repo root — must report the repo's .boukensha
printf '/exit\n' | ./week1_baseline/bin/ruby/09_global_executable | grep 'config:'

# 3. The point of the change: from a deep subdirectory, still the repo's config
cd week1_baseline/python/08_the_repl_loop/tests && printf '/exit\n' | boukensha | grep 'config:'

# 4. Outside any project, with the symlink removed — falls back to ~/.boukensha
cd /tmp && printf '/exit\n' | boukensha

# 5. The explicit override still wins over project detection
cd /path/to/repo && BOUKENSHA_DIR=/tmp/other printf '/exit\n' | boukensha | grep 'config:'

# 6. No hang at the filesystem root — the loop terminates
cd / && printf '/exit\n' | boukensha
```

Expected: (2) and (3) both print the repo root `.boukensha`; (4) prints the home path or exits
with the settings error, per the §3.4 decision; (5) prints `/tmp/other`; (6) returns promptly
rather than spinning.

Check 6 matters: `Pathname.new("/").parent` returns `/`, so a loop without the
`return nil if parent == dir` guard never terminates. It is the one way this change can hang a
global command rather than merely misconfigure it.

Reinstall before checks 3-6, since they exercise the installed copy rather than the repo:

```bash
cd week1_baseline/ruby/09_global_executable && gem build boukensha.gemspec && gem install ./boukensha-0.9.0.gem
```

---

## 5. Open question

`ruby_step_09_runnable.md` §3.1 is still unruled — step 08's 401 error message is absent in step
09. Unrelated to this change; flagging so it does not get lost.
