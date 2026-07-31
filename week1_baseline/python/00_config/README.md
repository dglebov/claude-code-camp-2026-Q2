# 00 · Configuration (Python)

Python port of `week1_baseline/ruby/00_config`. See that directory's README for the original
design rationale — this file documents the port and the places Python forced a change.

> Requires the shared environment. If you haven't run `uv sync` in `week1_baseline/python`, do
> that first — see [`../README.md`](../README.md).

We want to manage all configuration from an external file, e.g. `~/.boukensha/settings.yaml`,
via a dedicated `Config` class. Configuration is organised by **task** — a role in the agentic
loop bound to its own LLM. week1_baseline drives a single `player` task.

## Code map

| File | Purpose | Ruby original |
|------|---------|---------------|
| `boukensha/config.py` | `Config` class | `lib/boukensha/config.rb` |
| `boukensha/tasks/base.py` | abstract `Base` (provider/model + prompt resolution) | `lib/boukensha/tasks/base.rb` |
| `boukensha/tasks/player.py` | concrete `Player` (the main loop) | `lib/boukensha/tasks/player.rb` |
| `boukensha/env_file.py` | minimal `.env` loader | *(the `dotenv` gem)* |
| `boukensha/__init__.py` | top-level exports | `lib/boukensha.rb` |
| `prompts/system.md` | default system prompt shipped with the library | same |
| `examples/example.py` | runnable smoke-test | `examples/example.rb` |
| `conftest.py`, `tests/` | pytest suite | *(no Ruby equivalent)* |

---

## Config directory resolution

Unchanged from Ruby — **both ports read the same directory**:

1. **`BOUKENSHA_DIR` env var** — set this to point at any directory you like.
2. **`~/.boukensha`** — the default location for a real install.

## Config directory structure

```
.boukensha/
  .env                 # credentials, e.g. LLM API keys (never committed)
  settings.yaml        # all non-secret settings
  prompts/
    <task>/
      system.md        # per-task override of the default system prompt (optional)
```

## System prompt resolution

Per task, `Player.system_prompt` resolves in this order:

1. **`.boukensha/prompts/<task>/system.md`** — used when the task's `prompt_override.system` is
   `true` and the file exists.
2. **`prompts/system.md`** — the default shipped with the library. Note there is **no** per-task
   subfolder at this level.

## Usage

```python
from boukensha import Config
from boukensha.tasks import Player

config = Config()
player_settings = config.tasks("player")

Player.provider(player_settings)
Player.system_prompt(
    player_settings,
    user_prompts_dir=config.user_prompts_dir,
    default_prompts_dir=Config.PROMPTS_DIR,
)
```

## Configuration schema

- `tasks`: map of task name → task config (provider, model, prompt_override).
- `tasks.<name>.prompt_override.system`: when `true`, the task's
  `.boukensha/prompts/<name>/system.md` overrides the default system prompt.
- `mud`: MUD connection information for the main player.

```yaml
tasks:
  player:
    provider: anthropic        # provider name (string)
    model: claude-haiku-4-5
    prompt_override:
      system: true
mud:
  host: localhost
  port: 4000
  username: dummy
  password: helloworld
```

---

## Differences from the Ruby original

Behaviour is identical; these are the things Python made us spell differently.

| Ruby | Python | Why |
|------|--------|-----|
| `value \|\| default` | `_default(value, fallback)` with an `is None` check | Ruby treats `0` and `""` as truthy, Python does not. A configured `port: 0` would otherwise silently become `4000`. |
| `settings[k.to_s] \|\| settings[k.to_sym]` | plain string lookup | Python has no symbols; YAML keys are always `str`. |
| `prompt_override?` | `prompt_override` | `?` is not legal in a Python identifier. |
| `to_s` / `inspect` | `__str__` / `__repr__` | Output format is unchanged: `#<Boukensha::Config …>`. |
| `ArgumentError` | `ValueError` | Closest equivalent. Message text preserved verbatim. |
| `config.mud_host` (method) | `config.mud_host` (property) | Keeps call sites identical. `tasks()` stays a method — it takes an argument. |
| `Dotenv.load` | `boukensha/env_file.py` | Avoids a dependency. Same non-overriding semantics. |
| `raise NoMethodError` on nil settings | `ValueError` | A missing `tasks:` block now reports `tasks.player.provider is required in settings.yaml` instead of an opaque attribute error. |

## Run

```bash
./week1_baseline/bin/python/00_config
```

Expected output (values from your `.boukensha/`):

```
=== Boukensha Step 0: Configuration ===

Config dir:     /Users/you/Sites/Claude-Code-Camp/.boukensha
Tasks:          player

-- player task --
Provider:       anthropic
Model:          claude-haiku-4-5
Prompt override?true
System prompt:  You are a MUD player assistant. Use the tools available to y...

MUD host:       localhost:4000
MUD user:       dummy

API key set?    true

#<Boukensha::Config dir=/Users/you/Sites/Claude-Code-Camp/.boukensha tasks=player>
```

Booleans print as Ruby's `true`/`false`, not Python's `True`/`False`, so the two runs diff clean.

## Test

```bash
cd week1_baseline/python
uv run pytest 00_config
```
