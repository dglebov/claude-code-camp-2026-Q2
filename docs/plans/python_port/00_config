# Python Port Plan — Step 00 · Configuration

Port `week1_baseline/ruby/00_config` to `week1_baseline/python/00_config`.

**Scope:** week1 only, step 00 only. Do not touch `week0_explore`, `week2_capable`, or any
Ruby iteration. Do not modify the Ruby source — this is an additive port; the Ruby tree stays
the reference implementation.

---

## 1. Decisions (already settled — do not re-litigate)

| Decision | Choice |
|----------|--------|
| Packaging | `uv` + `pyproject.toml` + `uv.lock` (matches `week0_explore/circlemud-world-parser`) |
| YAML | `PyYAML`, via `yaml.safe_load` — direct analogue of Ruby's `YAML.safe_load` |
| Structure | Mirror Ruby 1:1 — same module/class/method names, stateless classmethods taking a settings dict |
| Tests | `pytest` covering `Config` + tasks |

Rationale for 1:1 mirroring: iterations 01–12 will follow. Keeping the trees structurally
diffable is worth more than Python elegance in a step-by-step course.

---

## 2. Reference files — what to port

Everything to port lives under `week1_baseline/ruby/00_config/`. Read **all** of these before
writing code; several behaviours are only obvious from the README.

| Read this (source of truth) | Purpose | Becomes |
|---|---|---|
| `README.md` | **Read first.** Defines the config-dir contract, prompt-resolution order, config schema, and the exact expected example output | `week1_baseline/python/00_config/README.md` (adapted) |
| `lib/boukensha/config.rb` | `Boukensha::Config` — dir resolution, `.env` loading, `settings.yaml` loading, `tasks`, `dig`, MUD accessors | `boukensha/config.py` |
| `lib/boukensha/tasks/base.rb` | Abstract stateless `Tasks::Base` — provider/model lookup, prompt override resolution | `boukensha/tasks/base.py` |
| `lib/boukensha/tasks/player.rb` | Concrete `Tasks::Player`, only defines `task_name = "player"` | `boukensha/tasks/player.py` |
| `lib/boukensha.rb` | Top-level require aggregator | `boukensha/__init__.py` |
| `examples/example.rb` | Runnable smoke test; its printed output is the parity target | `examples/example.py` |
| `prompts/system.md` | Default system prompt shipped with the library | `prompts/system.md` (copy verbatim) |
| `Gemfile` | Declares the sole dep (`dotenv`) | `pyproject.toml` |

Also read, for context only (do not port):

- `week1_baseline/ITERATIONS.md` — §"0 Configuration" and the design constraints
  ("avoid Agent SDKs", "use stdlib as much as possible", REST-direct philosophy).
- `week1_baseline/bin/00_config` — the Ruby launcher; the Python launcher mirrors its shape.

---

## 3. Shared runtime contract — the `.boukensha` directory

**Both ports read the same directory.** This is the whole point of the config step; do not
create a Python-specific config dir.

Resolution order (identical in both languages):

1. `BOUKENSHA_DIR` environment variable
2. `~/.boukensha` (default)

Expected structure:

```
.boukensha/
  .env            # secrets, e.g. ANTHROPIC_API_KEY — gitignored, never committed
  settings.yaml   # all non-secret settings
  prompts/
    <task>/
      system.md   # optional per-task override of the default system prompt
```

In this repo the live directory is `/Users/dglebov/claude-code-camp-2026-Q2/.boukensha`, and
`examples/example.rb` points `BOUKENSHA_DIR` at it so the example runs from a source checkout.
The Python example must resolve to **the same absolute path**, but note the depth differs —
compute it from `__file__` and verify, do not copy the Ruby `../../../../` literal blindly.

Prompt resolution order (per task), from README §"System prompt resolution":

1. `.boukensha/prompts/<task>/system.md` — used only when `prompt_override.system` is `true`
   **and** the file exists
2. `prompts/system.md` — the default shipped with the library (note: **no** per-task subfolder
   at this level)

---

## 4. Target layout

```
week1_baseline/python/00_config/
  pyproject.toml
  uv.lock
  .python-version
  README.md
  boukensha/
    __init__.py
    config.py
    tasks/
      __init__.py
      base.py
      player.py
  prompts/
    system.md
  examples/
    example.py
  tests/
    test_config.py
    test_tasks.py
```

`week1_baseline/python/00_config/` already exists and is empty.

---

## 5. Ruby → Python semantic gaps

These are the traps. Each one is a real behavioural difference, not style.

**5.1 — `||` truthiness. The highest-risk item.**
Ruby treats only `nil` and `false` as falsy; `0` and `""` are truthy. Python treats `0`, `""`,
`[]`, and `{}` as falsy. So `dig(:mud, :port) || 4000` returns `0` in Ruby but `4000` in Python
if the port is `0`. Use explicit `is None` checks for every defaulting expression, not `or`.

**5.2 — Symbol/string key duality.**
Ruby code is littered with `settings[key.to_s] || settings[key.to_sym]` because YAML keys may
load as either. Python has no symbols — YAML keys are always `str`. Collapse to plain string
lookup. Keep the helper function (`fetch`, `dig`) so the shape still matches Ruby.

**5.3 — `Config#dig`.**
Ruby's custom `dig` reduces over a key path, returning `nil` on any non-Hash node. Python's
`dict.get` does not chain. Implement the same reduce-with-guard helper.

**5.4 — Path handling.**
- `File.expand_path("../../prompts", __dir__)` → `Path(__file__).resolve().parent.parent / "prompts"`
- `Pathname.new(raw).expand_path` expands `~` **and** absolutises → `Path(raw).expanduser().resolve()`
- `File.join(Dir.home, ".boukensha")` → `Path.home() / ".boukensha"`
- Store `dir` as `str` if mirroring Ruby's `attr_reader :dir` output exactly in `__str__`.

**5.5 — dotenv override semantics.**
Ruby's `Dotenv.load` does **not** overwrite already-set environment variables. `python-dotenv`'s
`load_dotenv` defaults to `override=False`, which matches — but state it explicitly rather than
relying on the default.

**5.6 — Stateless class methods.**
`class << self; private` in `base.rb` makes `fetch`, `read_user_prompt`, `read_default_prompt`,
`read_file` private class methods. Use `@classmethod` with a leading underscore. `task_name`
must stay overridable by subclasses — `Player` overrides it, `Base` raises `NotImplementedError`.

**5.7 — Exceptions.**
`ArgumentError` → `ValueError`. `NotImplementedError` exists in both with the same meaning.
Preserve the message text (`"tasks.player.provider is required in settings.yaml"`) — the
filename in that message is `settings.yaml`, deliberately.

**5.8 — `to_s` / `inspect`.**
Ruby defines `to_s` and aliases `inspect` to it. Map to `__str__` and `__repr__` (both, so
that `print(config)` and a bare REPL echo match). Exact target format:
`#<Boukensha::Config dir=... tasks=...>` — keep the Ruby-style name; it is what the README's
expected output shows.

**5.9 — Safe navigation + slice in the example.**
`&.slice(0, 60)` yields `nil` when the prompt is missing, and Ruby interpolates `nil` as the
empty string. Python must print an empty string, **not** `None`.

**5.10 — `YAML.safe_load` returning nil.**
An empty `settings.yaml` yields `nil` in Ruby / `None` in Python. Both must coerce to `{}`.

---

## 6. Implementation steps

Work in this order; each step should leave the tree runnable.

1. **Scaffold** — `uv init` in `week1_baseline/python/00_config`, set `requires-python`, add
   `pyyaml` + `python-dotenv` deps and a `pytest` dev group. Match the `[tool.ruff]`
   `line-length = 120` convention from `week0_explore/circlemud-world-parser/pyproject.toml`.
   Pin `.python-version` (see open question Q2).
2. **`boukensha/config.py`** — port `config.rb`. Constants `DEFAULT_DIR`, `PROMPTS_DIR`;
   `__init__` doing resolve-dir → load-env → load-settings **in that order** (`.env` must load
   before settings so env-var expansion works in later iterations); `tasks()`,
   `user_prompts_dir`, `mud_host/port/username/password`, `dig()`, `__str__`/`__repr__`.
   Apply §5.1 to every default.
3. **`boukensha/tasks/base.py`** — port `base.rb` including the four private helpers.
4. **`boukensha/tasks/player.py`** — trivial subclass, `task_name = "player"`.
5. **`boukensha/__init__.py`** — re-export `Config` and `Player` so
   `from boukensha import Config` works, mirroring `lib/boukensha.rb`.
6. **`prompts/system.md`** — copy verbatim from the Ruby tree.
7. **`examples/example.py`** — port `example.rb` line-for-line. Output parity is the acceptance
   test; see §7.
8. **Launcher** — add the shell wrapper (see open question Q1).
9. **`tests/`** — see §7.
10. **`README.md`** — adapt the Ruby README: same contract sections, Python run instructions.

---

## 7. Verification

**Output parity (primary acceptance test).**
Run both and diff:

```bash
cd week1_baseline
bash bin/00_config                                         # ruby
cd python/00_config && uv run python examples/example.py   # python
```

Both must print the same block. Current known-good Ruby output:

```
=== Boukensha Step 0: Configuration ===

Config dir:     /Users/dglebov/claude-code-camp-2026-Q2/.boukensha
Tasks:          player

-- player task --
Provider:       anthropic
Model:          claude-sonet-5
Prompt override?true
System prompt:  You are MUD journet Player agent. You are playing the MUD on...

MUD host:       localhost:4000
MUD user:       dummy

API key set?    true

#<Boukensha::Config dir=/Users/dglebov/claude-code-camp-2026-Q2/.boukensha tasks=player>
```

Two literal-output traps: Ruby prints booleans as `true`/`false`, Python as `True`/`False`
(affects the `Prompt override?` and `API key set?` lines), and `Prompt override?` has no space
before the value in the Ruby source. Match Ruby exactly.

**pytest coverage.** Target the failure modes actually hit while debugging the Ruby version —
every one of these was a real bug:

- `BOUKENSHA_DIR` honoured; falls back to `~/.boukensha` when unset
- missing `settings.yaml` → `{}`, not a crash
- empty `settings.yaml` → `{}` (§5.10)
- filename is `settings.yaml`, not `settings.yml`
- `.env` loaded from the config dir; absent `.env` is not an error
- `dig()` returns `None` through a missing/non-dict node
- `mud_port` default of `4000` — **and** that an explicit `0` survives (§5.1)
- default prompt resolves from `prompts/system.md` with no per-task subfolder
- override used only when `prompt_override.system` is `true` **and** the file exists
- override flag `true` but file missing → silently falls back to default
- `provider`/`model` missing → `ValueError` with the `settings.yaml` message
- `Base.task_name` raises `NotImplementedError`; `Player.task_name == "player"`

Use `tmp_path` fixtures with a synthetic `.boukensha`; do not depend on the developer's real
config dir.

---

## 8. Open questions

**Q1 — Launcher name and location.**
The Ruby launcher is `week1_baseline/bin/00_config` (`cd ../ruby/00_config && bundle exec ruby
examples/example.rb`). Options: (a) `week1_baseline/bin/00_config_py`, (b) split into
`bin/ruby/00_config` + `bin/python/00_config`, (c) teach the existing `bin/00_config` a
`--python` flag. Proposed: **(a)** — additive, leaves the Ruby launcher untouched.

    - create a new directory dedicated one for ruby and python use bin directory and fix pathing for ruby 


**Q2 — Python version.**
`week0_explore/circlemud-world-parser` pins `3.14`, but your system `python3` is `3.9.6`, so
`uv` would fetch a managed 3.14. Pin `3.14` for consistency, or something lower to reduce
friction?

    - use the best option, I would go with UV 

**Q3 — Is `dotenv` acceptable as a dependency?**
`ITERATIONS.md` says use stdlib where possible, and the Ruby side took `dotenv` as its one
exception. Mirror that with `python-dotenv`, or hand-roll the ~10-line parser to keep PyYAML as
the only dependency?

    - keep as low dependencies as possibe 

**Q4 — Does the Python port get its own `pyproject.toml` per iteration?**
The Ruby tree gives each step its own `Gemfile` (self-contained, copy-forward). Confirm the
Python tree should do the same — one `pyproject.toml`/`uv.lock` per `NN_step` directory —
rather than one shared workspace at `week1_baseline/python/`.

    - Create an python enviroment and add that to the Python's README at the top, we should expect the user to create teh enviroment base on our instructions and assume the enivomrent will be there, maybe the venv should be loaded at root of the project because we will be creating iterations in future folders and having a single python env in a single place will make things easier.

**Q5 — Package name collision across iterations.**
Every step will define a package literally named `boukensha`. Self-contained per-directory
projects handle this fine as long as they are never installed into one shared environment.
Confirm each step gets its own `.venv`.

    - make it work 
---

## 9. Notes / observations (not action items)

- `.boukensha/settings.yaml` currently reads `model: claude-sonet-5` — a typo for
  `claude-sonnet-5`. Left as-is deliberately; the port must reproduce the config faithfully,
  not silently correct it. Flagging in case you want it fixed on the Ruby side first.
- `.boukensha/.env` currently holds the placeholder `ANTHROPIC_API_KEY="not_real_key"`. Step 00
  only checks presence, so this is sufficient for parity, but step 04 (`api_client`) will need
  a real key.
- `week1_baseline/bin/prompts/player/system.md` and `week1_baseline/bin/.env` are leftover
  copies whose content now lives in `.boukensha/` and `ruby/00_config/prompts/`. They are not
  read by any code. Out of scope here, but worth deleting separately.
