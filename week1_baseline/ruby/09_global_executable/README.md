# Step 9 — Global Executable

Package BOUKENSHA as a gem so the `boukensha` command works from anywhere on your machine.

## What this step adds

- `boukensha.gemspec` — declares the gem: name, version, which files to include, and the `bin/boukensha` executable
- `bin/boukensha` — the shebang script that becomes the global command
- `lib/boukensha_loader.rb` — resolves *which step folder* to load from, then boots the REPL
- `lib/boukensha.rb` + `lib/boukensha/` — step 8's lib, bundled as the default

## Run from the repo

```bash
./week1_baseline/bin/ruby/09_global_executable
```

No environment setup needed — the step finds the repo's own `.boukensha` by walking up from the
working directory. See **Where config comes from** below.

## Install globally

```bash
cd week1_baseline/ruby/09_global_executable
gem build boukensha.gemspec
gem install boukensha-0.9.0.gem
```

After that, `boukensha` is on your `$PATH` and works from any directory.

## Where config comes from

`settings.yaml`, `.env`, and any prompt overrides are read from a `.boukensha` directory, resolved
in this order:

| Priority | Source | Notes |
|----------|--------|-------|
| 1 | `BOUKENSHA_DIR` env var | Explicit override; always wins |
| 2 | The nearest `.boukensha` at or above the working directory | Walks up to `/`, like `git` finding `.git` |
| 3 | `~/.boukensha` | Fallback when you are not inside a project |

Tier 2 is what makes `boukensha` usable per-project: `cd` anywhere inside a project that has a
`.boukensha` directory — its root or any subdirectory — and the command picks it up. Step 08
checked only the exact working directory, so it worked from the project root and silently fell
back to home from anywhere below it.

If none of the three resolve to a directory holding a `settings.yaml`, the command exits with
`tasks.player.model is required in settings.yaml`.

## Switching steps with BOUKENSHA_PATH

The loader resolves in this order:

| Priority | Source | Example |
|----------|--------|---------|
| 1 | `BOUKENSHA_PATH` env var | `BOUKENSHA_PATH=~/Sites/boukensha/08_the_repl_loop boukensha` |
| 2 | `~/.boukensharc` file | `echo ~/Sites/boukensha/08_the_repl_loop > ~/.boukensharc` |
| 3 | Bundled default | just run `boukensha` |

`BOUKENSHA_PATH` must point to a step folder that contains `lib/boukensha.rb`.

Note that `BOUKENSHA_PATH` selects the *step library*; `BOUKENSHA_DIR` selects the *config
directory*. They are independent.

## Running a specific step

```bash
# step 8 (interactive REPL)
BOUKENSHA_PATH=~/Sites/boukensha/08_the_repl_loop boukensha

# step 7 doesn't have a REPL — loader tells you how to run it
BOUKENSHA_PATH=~/Sites/boukensha/07_the_run_dsl boukensha
# => boukensha: the step at .../07_the_run_dsl does not support the interactive REPL
#    Run its examples directly, e.g.: ruby .../07_the_run_dsl/examples/*.rb
```

## Debug mode

```bash
BOUKENSHA_DEBUG=1 boukensha
# => [boukensha] loading from: /path/to/step
```

## The key idea

The gem is just a **wrapper and a default**. All the teaching material stays in the numbered step folders exactly as it was. The gem doesn't copy or symlink anything — it just knows where to look.
