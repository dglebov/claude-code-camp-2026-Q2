# Step 08 REPL Loop — Fix Ruby, Port to Python — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `week1_baseline/ruby/08_the_repl_loop` actually run, and add the matching `week1_baseline/python/08_the_repl_loop` port with tests, so step 08 exists and works in both trees.

**Architecture:** Step 08 adds an interactive REPL on top of step 07's `Boukensha.run` DSL. A `Repl` object owns one long-lived `Context` and constructs a fresh `Agent` per turn, so conversation history accumulates. The Ruby side already has this code but shipped with two miscounted relative paths and no launcher. The Python side does not exist; it is a copy-forward of `python/07_the_run_dsl` plus the same five library deltas the Ruby step made over its own step 07.

**Tech Stack:** Ruby 3.x + Bundler (no test framework in the Ruby tree). Python 3.x + pytest, run through `uv`. Bash launchers under `week1_baseline/bin/`.

## Global Constraints

- **Path depth invariants** (enforced by `week1_baseline/bin/ruby/check-paths`): `BOUKENSHA_DIR` is 4 levels up from `examples/`; `PROMPTS_DIR` is 2 levels up from `lib/boukensha/`. In the Python tree the equivalents are `Path(__file__).resolve().parents[4] / ".boukensha"` and `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` + `"prompts"`.
- **Each step directory is a self-contained snapshot.** Never import across step directories. Every step ships its own `boukensha` package.
- **Python tests never run as one pytest process.** Use `week1_baseline/python/run-tests`, which runs each step in its own interpreter — every step ships a package literally named `boukensha`.
- **Never make a real API call in a test or a smoke run.** All verification below is offline.
- **`week1_baseline/ruby/08_the_repl_loop/` is currently untracked.** It enters git for the first time in Task 1, already fixed.
- **The repo is worked on directly on `main`** — no feature branches.
- **Ruby step README titles match their directory number** (`08_the_repl_loop` → `# Step 8 — …`).

---

### Task 1: Fix the Ruby step

**Files:**
- Modify: `week1_baseline/ruby/08_the_repl_loop/examples/example.rb:1,10-12`
- Modify: `week1_baseline/ruby/08_the_repl_loop/lib/boukensha/config.rb:13`
- Modify: `week1_baseline/ruby/08_the_repl_loop/README.md:1,5,43,49,54,57,69-72`
- Modify: `week1_baseline/ruby/07_the_run_dsl/README.md:1`
- Create: `week1_baseline/bin/ruby/08_the_repl_loop`
- Test: `week1_baseline/bin/ruby/check-paths` (the repo's own checker — there is no Ruby unit-test suite)

**Interfaces:**
- Consumes: nothing.
- Produces: a runnable `week1_baseline/bin/ruby/08_the_repl_loop` launcher. Task 2 reads the fixed `config.rb` and `example.rb` as the reference for the Python port, so this task must land first.

> **Note:** Steps 1a–1e may already be applied on disk from an earlier session. Run Step 1 (the checker) first — if it reports the three FAILs, apply 1a–1e; if it already passes, skip to Step 3.

- [ ] **Step 1: Run the checker to see the failures**

Run: `week1_baseline/bin/ruby/check-paths`

Expected: exit 1 with exactly these three lines:

```
FAIL 08_the_repl_loop  BOUKENSHA_DIR -> …/week1_baseline/.boukensha (does not exist)
FAIL 08_the_repl_loop  PROMPTS_DIR -> …/week1_baseline/ruby/prompts (does not exist)
FAIL 08_the_repl_loop  launcher missing or not executable: bin/ruby/08_the_repl_loop
```

- [ ] **Step 1a: Fix the config-directory depth**

In `week1_baseline/ruby/08_the_repl_loop/examples/example.rb`, line 1:

```ruby
ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../../.boukensha", __dir__)
```

(was `"../../../.boukensha"` — three levels reached `week1_baseline/`, which has no `.boukensha`)

- [ ] **Step 1b: Fix the prompts-directory depth**

In `week1_baseline/ruby/08_the_repl_loop/lib/boukensha/config.rb`, line 13:

```ruby
    PROMPTS_DIR = File.expand_path("../../prompts", __dir__).freeze
```

(was `"../../../prompts"` — three levels reached `week1_baseline/ruby/`, which has no `prompts`)

- [ ] **Step 1c: Point the tool sandbox at this step**

In `week1_baseline/ruby/08_the_repl_loop/examples/example.rb`, lines 10-12:

```ruby
# The base directory tools will operate relative to — this step's own folder makes
# a good playground since it already has source files to read.
base_dir = File.expand_path("..", __dir__)
```

(was `File.expand_path("../../07_the_run_dsl", __dir__)`, so step 08's REPL browsed step 07's source)

- [ ] **Step 1d: Renumber the README and fix its run instructions**

In `week1_baseline/ruby/08_the_repl_loop/README.md`, apply all six renumberings:

| Line | From | To |
|---|---|---|
| 1 | `# Step 7 — The REPL Loop` | `# Step 8 — The REPL Loop` |
| 5 | `\| \| Step 6 \| Step 7 \|` | `\| \| Step 7 \| Step 8 \|` |
| 43 | `## Changes from step 6` | `## Changes from step 7` |
| 49 | `Before step 7, the agent returned…` | `Before step 8, the agent returned…` |
| 54 | `# step 6 — final text returned but NOT in context` | `# step 7 — final text returned but NOT in context` |
| 57 | `# step 7 — final text added to context, then returned` | `# step 8 — final text added to context, then returned` |

Then replace the `## Running it` code block (lines 69-72), which names two paths that do not exist:

````markdown
```
cd 08_the_repl_loop
ANTHROPIC_API_KEY=your_key bundle exec ruby examples/example.rb
```

Or from anywhere in the repo, via the launcher:

```
./week1_baseline/bin/ruby/08_the_repl_loop
```
````

- [ ] **Step 1e: Fix step 07's title, the source of the shift**

In `week1_baseline/ruby/07_the_run_dsl/README.md`, line 1:

```markdown
# Step 7 — The Boukensha.run DSL
```

(was `# Step 6 — The Boukensha.run DSL`; `06_the_logger` correctly says `Step 6`, so two adjacent READMEs both claimed to be step 6)

- [ ] **Step 2: Create the launcher**

Create `week1_baseline/bin/ruby/08_the_repl_loop`, modelled verbatim on `bin/ruby/07_the_run_dsl`:

```bash
#!/usr/bin/env bash

cd "$(dirname "$0")/../../ruby/08_the_repl_loop"
bundle exec ruby examples/example.rb
```

Then: `chmod 755 week1_baseline/bin/ruby/08_the_repl_loop`

- [ ] **Step 3: Run the checker to verify it passes**

Run: `week1_baseline/bin/ruby/check-paths`

Expected: exit 0, output `All Ruby steps: paths resolve, launchers present.`

- [ ] **Step 4: Smoke-test the REPL offline**

Run: `printf '/help\n/exit\n' | ./week1_baseline/bin/ruby/08_the_repl_loop`

Expected: the `BOUKENSHA MUD Assistant (v0.8.0)` banner, then the five-line command list, then `Goodbye.`. No API call is made — `/help` and `/exit` are handled before any agent runs, so no key is needed.

- [ ] **Step 5: Verify the silent bug is actually gone**

The `PROMPTS_DIR` fix is invisible in Step 4 — a broken one yields `system_prompt == nil`, which only fails later as a provider 400. Assert it directly:

```bash
cd week1_baseline/ruby/08_the_repl_loop
BOUKENSHA_DIR="$(cd ../../.. && pwd)/.boukensha" ruby -Ilib -e '
require "boukensha"
cfg = Boukensha.config
sp = Boukensha::Tasks::Player.system_prompt(
  cfg.tasks(Boukensha::Tasks::Player.task_name),
  user_prompts_dir: cfg.user_prompts_dir,
  default_prompts_dir: Boukensha::Config::PROMPTS_DIR)
raise "system prompt is nil" if sp.nil? || sp.strip.empty?
puts "system prompt OK (#{sp.length} chars)"
'
```

Expected: `system prompt OK (N chars)`, non-zero N. Fails loudly if `PROMPTS_DIR` ever regresses.

- [ ] **Step 6: Check no stale references survive**

Run: `grep -rn 'step7\|07_the_repl_loop\|Step 6' week1_baseline/ruby/08_the_repl_loop/`

Expected: no output.

- [ ] **Step 7: Commit — the whole step enters git already fixed**

```bash
git add week1_baseline/ruby/08_the_repl_loop week1_baseline/bin/ruby/08_the_repl_loop week1_baseline/ruby/07_the_run_dsl/README.md
git commit -m "ruby step 08: the repl loop"
```

---

### Task 2: Scaffold the Python step and port the five library deltas

**Files:**
- Create: `week1_baseline/python/08_the_repl_loop/` (copied from `07_the_run_dsl/`)
- Modify: `week1_baseline/python/08_the_repl_loop/boukensha/context.py` (add `clear_messages`)
- Modify: `week1_baseline/python/08_the_repl_loop/boukensha/agent.py:80,127,133` (persist final reply)
- Modify: `week1_baseline/python/08_the_repl_loop/boukensha/client.py:145` (401 message)
- Modify: `week1_baseline/python/08_the_repl_loop/boukensha/config.py` (`_resolve_dir` cwd lookup)
- Test: `week1_baseline/python/08_the_repl_loop/tests/test_context.py`, `tests/test_agent.py`, `tests/test_client.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: the fixed Ruby step from Task 1 as the reference implementation.
- Produces: `Context.clear_messages()` (no args, returns `None`); `Agent.run()` now appends the final assistant text to `self._context` before returning it. Task 3's `Repl` depends on both.

- [ ] **Step 1: Copy step 07 forward**

```bash
cd week1_baseline/python
cp -R 07_the_run_dsl 08_the_repl_loop
find 08_the_repl_loop -name '__pycache__' -type d -exec rm -rf {} +
find 08_the_repl_loop -name '.pytest_cache' -type d -exec rm -rf {} +
```

- [ ] **Step 2: Confirm the copy is green before changing anything**

Run: `cd week1_baseline/python && ./run-tests 08_the_repl_loop`

Expected: `365 passed`. This is the baseline — every later count is this plus new tests.

- [ ] **Step 3: Update the ported-from headers**

Every module docstring in the copy begins `"""Port of \`ruby/07_the_run_dsl/lib/boukensha/<file>.rb\`.`. Repoint them:

```bash
cd week1_baseline/python/08_the_repl_loop
grep -rl 'ruby/07_the_run_dsl' boukensha tests conftest.py examples \
  | xargs sed -i '' 's|ruby/07_the_run_dsl|ruby/08_the_repl_loop|g'
```

Verify: `grep -rn '07_the_run_dsl' boukensha tests conftest.py examples` returns nothing.

- [ ] **Step 4: Write the failing test for `Context.clear_messages`**

Append to `week1_baseline/python/08_the_repl_loop/tests/test_context.py`:

```python
def test_clear_messages_drops_history(context):
    assert context.turn_count == 3
    context.clear_messages()
    assert context.turn_count == 0
    assert context.messages == []


def test_clear_messages_keeps_tools_and_system(context):
    context.clear_messages()
    assert context.tool_count == 2
    assert context.system == SYSTEM


def test_clear_messages_is_idempotent(empty_context):
    empty_context.clear_messages()
    empty_context.clear_messages()
    assert empty_context.turn_count == 0
```

`SYSTEM` is already imported by this file from `tests/conftest.py`; if it is not, add `from conftest import SYSTEM`.

- [ ] **Step 5: Run it to make sure it fails**

Run: `cd week1_baseline/python && uv run pytest 08_the_repl_loop/tests/test_context.py -q -k clear_messages`

Expected: FAIL, `AttributeError: 'Context' object has no attribute 'clear_messages'`

- [ ] **Step 6: Implement `clear_messages`**

In `week1_baseline/python/08_the_repl_loop/boukensha/context.py`, after `add_message`:

```python
    def clear_messages(self):
        """Drop all conversation history, keeping tools and system prompt intact.

        Used by the REPL's /clear command. Ruby names this `clear_messages!` — the bang suffix
        is not legal in a Python identifier, and there is no non-mutating counterpart to
        distinguish it from.
        """
        self.messages = []
```

- [ ] **Step 7: Run it to make sure it passes**

Run: `cd week1_baseline/python && uv run pytest 08_the_repl_loop/tests/test_context.py -q`

Expected: `18 passed` (15 existing + 3 new)

- [ ] **Step 8: Write the failing test for the agent persisting its final reply**

Append to `week1_baseline/python/08_the_repl_loop/tests/test_agent.py`. Match the fake-client style already used in that file — read the existing `test_agent.py` fixtures first and reuse them rather than inventing new ones:

```python
def test_run_appends_final_text_to_context(agent_with_text_reply):
    agent, ctx = agent_with_text_reply
    result = agent.run()
    assert ctx.messages[-1].role == "assistant"
    assert ctx.messages[-1].content == result


def test_run_appends_only_once(agent_with_text_reply):
    agent, ctx = agent_with_text_reply
    agent.run()
    assistant_msgs = [m for m in ctx.messages if m.role == "assistant"]
    assert len(assistant_msgs) == 1
```

If no `agent_with_text_reply` fixture exists, build the agent inline exactly as the neighbouring tests in `test_agent.py` do — do not add a fixture to `tests/conftest.py`, which is shared with the backend tests.

- [ ] **Step 9: Run it to make sure it fails**

Run: `cd week1_baseline/python && uv run pytest 08_the_repl_loop/tests/test_agent.py -q -k appends`

Expected: FAIL — the last message is the user turn, not an assistant reply.

- [ ] **Step 10: Persist the final reply in all three return paths**

In `week1_baseline/python/08_the_repl_loop/boukensha/agent.py`, mirroring `ruby/08_the_repl_loop/lib/boukensha/agent.rb`:

At line ~79, the completed path:

```python
                self._logger.turn_end(reason="completed", iterations=self._iteration)
                self._context.add_message("assistant", text)
                return text
```

At line ~126, the wind-down `ApiError` fallback:

```python
            self._logger.turn_end(reason=reason, iterations=self._iteration)
            self._context.add_message("assistant", msg)
            return msg
```

At line ~132, the wind-down success path:

```python
        self._logger.turn_end(reason=reason, iterations=self._iteration)
        self._context.add_message("assistant", text)
        return text
```

- [ ] **Step 11: Run the whole step's tests**

Run: `cd week1_baseline/python && ./run-tests 08_the_repl_loop`

Expected: all pass. If any pre-existing `test_agent.py` test asserted an exact `turn_count` or an exact final message, it now legitimately shifts by one — update those assertions to expect the trailing assistant message, and note the reason in the test.

- [ ] **Step 12: Write the failing test for the 401 message**

Append to `week1_baseline/python/08_the_repl_loop/tests/test_client.py`, reusing the stub-response helper already in that file:

```python
def test_401_reports_authentication_failure(...):
    # Arrange a stubbed 401 response exactly as the neighbouring non-2xx tests do.
    with pytest.raises(ApiError) as excinfo:
        client.call(...)
    assert "authentication failed (401)" in str(excinfo.value)
    assert "check your API key" in str(excinfo.value)
```

Fill the `...` from the existing non-2xx test in that file — it already constructs a client with a stubbed transport and asserts on `ApiError`.

- [ ] **Step 13: Run it to make sure it fails**

Run: `cd week1_baseline/python && uv run pytest 08_the_repl_loop/tests/test_client.py -q -k 401`

Expected: FAIL — the message is the generic `API request failed after N attempts (401): …`.

- [ ] **Step 14: Implement the 401 branch**

In `week1_baseline/python/08_the_repl_loop/boukensha/client.py`, before the existing non-2xx raise at line ~145:

```python
        if response.status == 401:
            raise ApiError("authentication failed (401) — check your API key")

        if not 200 <= response.status < 300:
            raise ApiError(
                f"API request failed after {attempts} attempt{'' if attempts == 1 else 's'} "
                f"({response.status}): {response.body}"
            )
```

- [ ] **Step 15: Write the failing test for the cwd config lookup**

Append to `week1_baseline/python/08_the_repl_loop/tests/test_config.py`:

```python
def test_resolve_dir_prefers_boukensha_env_var(tmp_path, monkeypatch):
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    (tmp_path / ".boukensha").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BOUKENSHA_DIR", str(explicit))
    assert Config().dir == str(explicit)


def test_resolve_dir_falls_back_to_cwd_boukensha(tmp_path, monkeypatch):
    cwd_dir = tmp_path / ".boukensha"
    cwd_dir.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BOUKENSHA_DIR", raising=False)
    assert Config().dir == str(cwd_dir)


def test_resolve_dir_falls_back_to_home_when_no_cwd_boukensha(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no .boukensha here
    monkeypatch.delenv("BOUKENSHA_DIR", raising=False)
    assert Config().dir == os.path.abspath(os.path.expanduser(Config.DEFAULT_DIR))
```

- [ ] **Step 16: Run it to make sure it fails**

Run: `cd week1_baseline/python && uv run pytest 08_the_repl_loop/tests/test_config.py -q -k resolve_dir`

Expected: `test_resolve_dir_falls_back_to_cwd_boukensha` FAILs — it currently returns the home default.

- [ ] **Step 17: Implement the three-tier lookup**

In `week1_baseline/python/08_the_repl_loop/boukensha/config.py`, replace `_resolve_dir`, mirroring `ruby/08_the_repl_loop/lib/boukensha/config.rb`:

```python
    def _resolve_dir(self):
        # 1. Explicit override
        raw = os.environ.get("BOUKENSHA_DIR")
        if raw is not None:
            # abspath (not realpath) matches Ruby's File.expand_path, which normalises without
            # resolving symlinks.
            return os.path.abspath(os.path.expanduser(raw))

        # 2. .boukensha in the current working directory
        cwd_dir = os.path.join(os.getcwd(), ".boukensha")
        if os.path.isdir(cwd_dir):
            return cwd_dir

        # 3. ~/.boukensha default
        return os.path.abspath(os.path.expanduser(self.DEFAULT_DIR))
```

- [ ] **Step 18: Run the full step suite**

Run: `cd week1_baseline/python && ./run-tests 08_the_repl_loop`

Expected: all pass, count is 365 + the new tests.

- [ ] **Step 19: Commit**

```bash
git add week1_baseline/python/08_the_repl_loop
git commit -m "python step 08: scaffold and port step 07->08 library deltas"
```

---

### Task 3: Port the REPL itself

**Files:**
- Create: `week1_baseline/python/08_the_repl_loop/boukensha/version.py`
- Create: `week1_baseline/python/08_the_repl_loop/boukensha/repl.py`
- Modify: `week1_baseline/python/08_the_repl_loop/boukensha/__init__.py` (add `repl()`, export `Repl` and `VERSION`)
- Test: `week1_baseline/python/08_the_repl_loop/tests/test_repl.py` (new)

**Interfaces:**
- Consumes: `Context.clear_messages()` and the reply-persisting `Agent.run()` from Task 2.
- Produces: `Repl(context=, registry=, builder=, client=, logger=, config_dir=None, provider=None, model=None, version=None, api_key=None, task_settings=None, max_iterations=None, max_output_tokens=None)` with a `.start()` method returning `None`; module-level `boukensha.repl(**kwargs)` taking every `boukensha.run` keyword except `task`; `boukensha.VERSION` as a string. Task 4's example calls `boukensha.repl`.

**Naming note for the implementer:** Ruby has no collision between the `Boukensha::Repl` constant and the `Boukensha.repl` method. Python does — `def repl(...)` in `__init__.py` rebinds the `boukensha.repl` attribute from the submodule to the function. This is harmless at runtime (the `Repl` class is already bound by name), but it means tests **cannot** patch `boukensha.repl.Agent` by dotted string. Use:

```python
import importlib
repl_mod = importlib.import_module("boukensha.repl")
monkeypatch.setattr(repl_mod, "Agent", FakeAgent)
```

`importlib.import_module` reads `sys.modules`, which still holds the real module. Keep the filename `repl.py` so it stays diffable against `repl.rb`, and document this collision in the module docstring.

- [ ] **Step 1: Create `version.py`**

`week1_baseline/python/08_the_repl_loop/boukensha/version.py`:

```python
"""Port of `ruby/08_the_repl_loop/lib/boukensha/version.rb`.

The version string the REPL banner prints. New in step 08.
"""

VERSION = "0.8.0"
```

- [ ] **Step 2: Write the failing tests for the REPL**

Create `week1_baseline/python/08_the_repl_loop/tests/test_repl.py`:

```python
"""Tests for the step-08 REPL loop."""

import importlib
import io

import boukensha
import pytest
from boukensha.context import Context
from boukensha.registry import Registry
from boukensha.repl import Repl
from boukensha.tasks import Player

SYSTEM = "You are a MUD player assistant."


class FakeAgent:
    """Stands in for Agent so no API call is made. Mirrors what the real one now does:
    append the reply to the context, then return it."""

    reply = "a fake reply"

    def __init__(self, *, context, **_kwargs):
        self._context = context

    def run(self):
        self._context.add_message("assistant", self.reply)
        return self.reply


class FakeLogger:
    def __init__(self):
        self.turns = []

    def turn(self, *, n):
        self.turns.append(n)

    def close(self):
        pass


@pytest.fixture
def repl_parts():
    ctx = Context(task=Player, system=SYSTEM)
    registry = Registry(ctx)
    logger = FakeLogger()
    return ctx, registry, logger


def build_repl(ctx, registry, logger, **overrides):
    kwargs = dict(
        context=ctx,
        registry=registry,
        builder=None,
        client=None,
        logger=logger,
        config_dir=None,
        provider="anthropic",
        model="claude-haiku-4-5",
        version="0.8.0",
        api_key="sk-test",
    )
    kwargs.update(overrides)
    return Repl(**kwargs)


def drive(monkeypatch, repl, keystrokes):
    """Feed `keystrokes` to the REPL as stdin and run it to completion."""
    monkeypatch.setattr("sys.stdin", io.StringIO(keystrokes))
    repl_mod = importlib.import_module("boukensha.repl")
    monkeypatch.setattr(repl_mod, "Agent", FakeAgent)
    repl.start()


def test_exit_command_stops_and_says_goodbye(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    drive(monkeypatch, build_repl(ctx, registry, logger), "/exit\n")
    assert "Goodbye." in capsys.readouterr().out


def test_quit_is_an_alias_for_exit(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    drive(monkeypatch, build_repl(ctx, registry, logger), "/quit\n")
    assert "Goodbye." in capsys.readouterr().out


def test_eof_leaves_the_loop(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    drive(monkeypatch, build_repl(ctx, registry, logger), "")
    assert "Goodbye." not in capsys.readouterr().out  # EOF exits silently, as Ruby's does


def test_help_lists_every_command(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    drive(monkeypatch, build_repl(ctx, registry, logger), "/help\n/exit\n")
    out = capsys.readouterr().out
    for command in ("/quiet", "/loud", "/clear", "/exit", "/help"):
        assert command in out


def test_blank_input_is_skipped(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    drive(monkeypatch, build_repl(ctx, registry, logger), "\n   \n/exit\n")
    assert logger.turns == []
    assert ctx.turn_count == 0


def test_a_normal_line_runs_a_turn(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    drive(monkeypatch, build_repl(ctx, registry, logger), "look around\n/exit\n")
    out = capsys.readouterr().out
    assert FakeAgent.reply in out
    assert logger.turns == [1]
    assert ctx.messages[0].role == "user"
    assert ctx.messages[0].content == "look around"


def test_history_accumulates_across_turns(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    drive(monkeypatch, build_repl(ctx, registry, logger), "first\nsecond\n/exit\n")
    assert logger.turns == [1, 2]
    assert [m.content for m in ctx.messages] == [
        "first", FakeAgent.reply, "second", FakeAgent.reply,
    ]


def test_clear_wipes_history_but_keeps_tools(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts

    @registry.tool("look", description="Look around", parameters={})
    def look():
        return "a room"

    drive(monkeypatch, build_repl(ctx, registry, logger), "first\n/clear\n/exit\n")
    assert ctx.turn_count == 0
    assert ctx.tool_count == 1
    assert "history cleared" in capsys.readouterr().out


def test_clear_resets_the_turn_counter(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    drive(monkeypatch, build_repl(ctx, registry, logger), "first\n/clear\nsecond\n/exit\n")
    assert logger.turns == [1, 1]


def test_quiet_and_loud_toggle_module_state(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    try:
        drive(monkeypatch, build_repl(ctx, registry, logger), "/quiet\n/exit\n")
        assert boukensha.is_quiet() is True
        drive(monkeypatch, build_repl(ctx, registry, logger), "/loud\n/exit\n")
        assert boukensha.is_quiet() is False
    finally:
        boukensha.loud()


def test_banner_reports_a_missing_api_key(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    drive(monkeypatch, build_repl(ctx, registry, logger, api_key=None), "/exit\n")
    assert "✗ API key not set" in capsys.readouterr().out


def test_banner_reports_a_present_api_key(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    drive(monkeypatch, build_repl(ctx, registry, logger), "/exit\n")
    assert "✓ API key set" in capsys.readouterr().out


def test_banner_reports_a_missing_config_dir(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts
    repl = build_repl(ctx, registry, logger, config_dir="/nope/not/here")
    drive(monkeypatch, repl, "/exit\n")
    assert "✗ directory not found" in capsys.readouterr().out


def test_api_error_in_a_turn_does_not_kill_the_loop(repl_parts, monkeypatch, capsys):
    ctx, registry, logger = repl_parts

    class ExplodingAgent:
        def __init__(self, **_kwargs):
            pass

        def run(self):
            raise boukensha.ApiError("boom")

    monkeypatch.setattr("sys.stdin", io.StringIO("first\n/exit\n"))
    repl_mod = importlib.import_module("boukensha.repl")
    monkeypatch.setattr(repl_mod, "Agent", ExplodingAgent)
    build_repl(ctx, registry, logger).start()
    out = capsys.readouterr().out
    assert "[error] API call failed: boom" in out
    assert "Goodbye." in out
```

- [ ] **Step 3: Run them to make sure they fail**

Run: `cd week1_baseline/python && uv run pytest 08_the_repl_loop/tests/test_repl.py -q`

Expected: collection error, `ModuleNotFoundError: No module named 'boukensha.repl'`

- [ ] **Step 4: Implement `repl.py`**

Create `week1_baseline/python/08_the_repl_loop/boukensha/repl.py`, porting `ruby/08_the_repl_loop/lib/boukensha/repl.rb` line for line:

```python
"""Port of `ruby/08_the_repl_loop/lib/boukensha/repl.rb`.

Repl is the interactive session loop. It wraps the same primitives as a single `boukensha.run`
call, but instead of running once it stays alive: it reads a task from the user, runs the agent,
prints the reply, and loops back to the prompt.

The Context is shared across every turn so conversation history accumulates naturally — the
agent sees the full transcript each time it is called.

Ruby has no collision between the `Boukensha::Repl` constant and the `Boukensha.repl` method.
Python does: `def repl(...)` in `__init__.py` rebinds the `boukensha.repl` attribute from this
module to that function. Harmless at runtime — `Repl` is bound by name before the rebind — but
tests must reach this module through `importlib.import_module("boukensha.repl")` rather than the
`boukensha.repl` attribute.
"""

import sys

from .agent import Agent
from .errors import ApiError, LoopError

PROMPT = "boukensha> "

HELP = """Commands:
  /quiet   suppress logging output
  /loud    re-enable logging output
  /clear   wipe conversation history (tools stay)
  /exit    leave the REPL
  /help    show this message
"""


class Repl:
    PROMPT = PROMPT
    HELP = HELP

    def __init__(
        self,
        *,
        context,
        registry,
        builder,
        client,
        logger,
        config_dir=None,
        provider=None,
        model=None,
        version=None,
        api_key=None,
        task_settings=None,
        max_iterations=None,
        max_output_tokens=None,
    ):
        self._context = context
        self._registry = registry
        self._builder = builder
        self._client = client
        self._logger = logger
        self._task_settings = task_settings
        self._max_iterations = max_iterations
        self._max_output_tokens = max_output_tokens
        self._config_dir = config_dir
        self._provider = provider
        self._model = model
        self._version = version
        self._api_key = api_key
        self._turn = 0

    def start(self):
        print(self._banner())

        while True:
            print(PROMPT, end="", flush=True)

            line = sys.stdin.readline()
            if line == "":  # EOF / Ctrl-D
                break

            entry = line.rstrip("\n").strip()
            if not entry:
                continue

            if entry in ("/exit", "/quit"):
                print("Goodbye.")
                break
            if entry == "/help":
                print(HELP)
                continue
            if entry == "/quiet":
                import boukensha

                boukensha.quiet()
                print("(logging suppressed — type /loud to re-enable)")
                continue
            if entry == "/loud":
                import boukensha

                boukensha.loud()
                print("(logging enabled)")
                continue
            if entry == "/clear":
                self._context.clear_messages()
                self._turn = 0
                print("(conversation history cleared)")
                continue

            self._run_turn(entry)

    def _banner(self):
        key_status = "✗ API key not set" if not (self._api_key or "").strip() else "✓ API key set"
        provider_line = f"{self._provider or 'default'} ({self._model or 'default'})  {key_status}"
        config_exists = self._config_dir and os.path.isdir(self._config_dir)
        config_line = (
            self._config_dir
            if config_exists
            else f"{self._config_dir or '(default)'}  ✗ directory not found"
        )
        ver = self._version or "?.?.?"
        padding = " " * max(0, 9 - len(ver))

        return (
            "\n"
            "╔══════════════════════════════════════╗\n"
            f"║  BOUKENSHA MUD Assistant (v{ver}){padding}║\n"
            "╚══════════════════════════════════════╝\n"
            f"  config:    {config_line}\n"
            f"  provider:  {provider_line}\n"
            "\n"
            "  /quiet or /loud   toggle logging\n"
            "  /clear           reset conversation history\n"
            "  /exit or /quit    leave the REPL\n"
        )

    def _run_turn(self, entry):
        self._turn += 1
        self._logger.turn(n=self._turn)

        self._context.add_message("user", entry)

        agent = Agent(
            context=self._context,
            registry=self._registry,
            builder=self._builder,
            client=self._client,
            logger=self._logger,
            task_settings=self._task_settings,
            max_iterations=self._max_iterations,
            max_output_tokens=self._max_output_tokens,
        )

        try:
            result = agent.run()
        except LoopError as error:
            print(f"\n[error] {error}")
            return
        except ApiError as error:
            print(f"\n[error] API call failed: {error}")
            return

        # Printed outside the logger so it stays visible even when boukensha.quiet() is active.
        print()
        print(result)
```

Add `import os` to the import block at the top — `_banner` uses `os.path.isdir`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd week1_baseline/python && uv run pytest 08_the_repl_loop/tests/test_repl.py -q`

Expected: `14 passed`. If `test_banner_reports_a_missing_config_dir` fails on padding width, fix `_banner`, not the test.

- [ ] **Step 6: Write the failing test for the `boukensha.repl` entry point**

Append to `week1_baseline/python/08_the_repl_loop/tests/test_repl.py`. Model the wiring assertions on the existing `tests/test_run.py`, which already covers the same plumbing for `boukensha.run`:

```python
def test_module_level_repl_wires_a_repl_and_starts_it(monkeypatch, config_dir):
    (config_dir / "settings.yaml").write_text(
        "tasks:\n  player:\n    provider: anthropic\n    model: claude-haiku-4-5\n",
        encoding="utf-8",
    )
    started = {}

    class FakeRepl:
        def __init__(self, **kwargs):
            started["kwargs"] = kwargs

        def start(self):
            started["started"] = True

    monkeypatch.setattr(boukensha, "Repl", FakeRepl)
    boukensha.repl()

    assert started["started"] is True
    assert started["kwargs"]["model"] == "claude-haiku-4-5"
    assert started["kwargs"]["provider"] == "anthropic"
    assert started["kwargs"]["version"] == boukensha.VERSION


def test_module_level_repl_registers_tools_from_the_block(monkeypatch, config_dir):
    (config_dir / "settings.yaml").write_text(
        "tasks:\n  player:\n    provider: anthropic\n    model: claude-haiku-4-5\n",
        encoding="utf-8",
    )
    captured = {}

    class FakeRepl:
        def __init__(self, **kwargs):
            captured["registry"] = kwargs["registry"]

        def start(self):
            pass

    def register(dsl):
        @dsl.tool("look", description="Look around", parameters={})
        def look():
            return "a room"

    monkeypatch.setattr(boukensha, "Repl", FakeRepl)
    boukensha.repl(block=register)

    assert captured["registry"].context.tool_count == 1
```

The `config_dir` fixture comes from the step-root `conftest.py` and is already available. If `Registry` exposes its context under a different attribute name, adjust the last assertion to match — check `boukensha/registry.py` first.

- [ ] **Step 7: Run it to make sure it fails**

Run: `cd week1_baseline/python && uv run pytest 08_the_repl_loop/tests/test_repl.py -q -k module_level`

Expected: FAIL, `AttributeError: module 'boukensha' has no attribute 'repl'`

- [ ] **Step 8: Implement `boukensha.repl`**

In `week1_baseline/python/08_the_repl_loop/boukensha/__init__.py`:

1. Add to the import block: `from .repl import Repl` and `from .version import VERSION`
2. Add `repl` after `run`. It is `run` minus `task`, ending in a `Repl(...).start()` instead of `agent.run()`. Copy `run`'s body verbatim from `cfg = config()` through `logger = Logger(...)`, then:

```python
        Repl(
            context=ctx,
            registry=registry,
            builder=builder,
            client=client,
            logger=logger,
            task_settings=task_settings,
            max_iterations=effective_max_iterations,
            max_output_tokens=effective_max_output_tokens,
            config_dir=cfg.dir,
            provider=backend,
            model=model,
            version=VERSION,
            api_key=api_key,
        ).start()
    except KeyboardInterrupt:
        # Ruby's `rescue Interrupt`. Ctrl-C leaves the REPL gracefully rather than dumping a
        # traceback.
        print("\nInterrupted.")
    finally:
        if logger is not None:
            logger.close()
```

Reference `Repl` through the module global so the test's `monkeypatch.setattr(boukensha, "Repl", FakeRepl)` takes effect — call it as a bare `Repl(...)`, which resolves through module globals at call time.

3. Add `"Repl"`, `"VERSION"`, and `"repl"` to `__all__`, keeping it alphabetically sorted: `"Registry"`, `"Repl"`, `"RunDSL"`, … `"quiet"`, `"repl"`, `"run"`, and `"VERSION"` in its sorted position among the uppercase names.

- [ ] **Step 9: Run the full step suite**

Run: `cd week1_baseline/python && ./run-tests 08_the_repl_loop`

Expected: all pass, `381 passed` or thereabouts (365 baseline + 3 context + 2 agent + 1 client + 3 config + 14 repl + 2 entry point, minus any pre-existing agent assertions you adjusted).

- [ ] **Step 10: Commit**

```bash
git add week1_baseline/python/08_the_repl_loop
git commit -m "python step 08: the repl loop"
```

---

### Task 4: Wire up the Python example, launcher, and docs

**Files:**
- Modify: `week1_baseline/python/08_the_repl_loop/examples/example.py`
- Modify: `week1_baseline/python/08_the_repl_loop/README.md`
- Create: `week1_baseline/bin/python/08_the_repl_loop`
- Modify: `week1_baseline/python/README.md:82-83,102-110`

**Interfaces:**
- Consumes: `boukensha.repl(block=...)` from Task 3.
- Produces: the final user-facing entry points. Nothing depends on this task.

- [ ] **Step 1: Rewrite the example as a REPL**

Replace `week1_baseline/python/08_the_repl_loop/examples/example.py` with the Python mirror of `ruby/08_the_repl_loop/examples/example.rb`:

```python
import os
import sys
from pathlib import Path

# Mirrors Ruby's `require_relative "../lib/boukensha"` — put the iteration root on sys.path so
# `boukensha` resolves without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boukensha

os.environ.setdefault("BOUKENSHA_DIR", str(Path(__file__).resolve().parents[4] / ".boukensha"))

# Config is loaded automatically inside boukensha.repl — system prompt, model,
# and API key all come from ~/.boukensha (or BOUKENSHA_DIR) by default.

print(f"Config: {boukensha.config()}")
print()

# The base directory tools will operate relative to — this step's own folder makes
# a good playground since it already has source files to read.
base_dir = Path(__file__).resolve().parent.parent


def register(dsl):
    @dsl.tool(
        "read_file",
        description="Read the contents of a file from disk",
        parameters={"path": {"type": "string", "description": "File path (relative to the working directory)"}},
    )
    def read_file(*, path):
        return (base_dir / path).read_text(encoding="utf-8")

    @dsl.tool(
        "list_directory",
        description="List the files in a directory",
        parameters={"path": {"type": "string", "description": "Directory path (relative to the working directory, or '.' for root)"}},
    )
    def list_directory(*, path):
        entries = sorted(p.name for p in (base_dir / path).iterdir() if not p.name.startswith("."))
        return ", ".join(entries)


boukensha.repl(block=register)
```

`parents[4]` is the repo root — verify with `python3 -c "from pathlib import Path; print(Path('week1_baseline/python/08_the_repl_loop/examples/example.py').resolve().parents[4])"`, which must print the repo root.

- [ ] **Step 2: Create the launcher**

Create `week1_baseline/bin/python/08_the_repl_loop`, modelled verbatim on `bin/python/07_the_run_dsl`:

```bash
#!/usr/bin/env bash

# Runs from the shared week1 Python environment at week1_baseline/python.
cd "$(dirname "$0")/../../python"
uv run python 08_the_repl_loop/examples/example.py
```

Then: `chmod 755 week1_baseline/bin/python/08_the_repl_loop`

- [ ] **Step 3: Smoke-test the Python REPL offline**

Run: `printf '/help\n/exit\n' | ./week1_baseline/bin/python/08_the_repl_loop`

Expected: the same banner shape the Ruby step prints, the command list, then `Goodbye.`. No API call.

- [ ] **Step 4: Compare the two banners**

Run:

```bash
diff <(printf '/help\n/exit\n' | ./week1_baseline/bin/ruby/08_the_repl_loop) \
     <(printf '/help\n/exit\n' | ./week1_baseline/bin/python/08_the_repl_loop)
```

Expected: differences only in the `Config:` line (Ruby prints `#<Boukensha::Config …>`, Python its own repr). If the banner box, command list, or `Goodbye.` differ, fix the Python side to match Ruby. Record whatever residual difference remains — it goes in the README in Step 6.

- [ ] **Step 5: Port the step README**

Rewrite `week1_baseline/python/08_the_repl_loop/README.md` from `ruby/08_the_repl_loop/README.md`, retitled `# Step 8 — The REPL Loop`, with:
- `Boukensha.repl` → `boukensha.repl`, `Context#clear_messages!` → `Context.clear_messages`, `Logger#turn` → `Logger.turn`
- a `## Python deviations` section recording: the `clear_messages` bang-suffix drop, the `boukensha.repl` module/function name collision, and `block=` in place of Ruby's `instance_eval` block — matching how `07_the_run_dsl/README.md` documents its own deviations
- a run block naming `./week1_baseline/bin/python/08_the_repl_loop`

- [ ] **Step 6: Update the Python tree README**

In `week1_baseline/python/README.md`, add the table row after line 82:

```markdown
| 08 · The REPL Loop | `08_the_repl_loop/` | `week1_baseline/bin/python/08_the_repl_loop` |
```

And update the exceptions paragraph at lines 102-110: `**Steps 04–07 are the exceptions.**` → `**Steps 04–08 are the exceptions.**`, add `[`08_the_repl_loop/README.md`](08_the_repl_loop/README.md)` to the list of linked READMEs, and add a sentence noting step 08 is interactive, so parity is checked by driving both launchers with the same piped keystrokes (the Step 4 command) rather than by a plain `diff`.

- [ ] **Step 7: Full verification across both trees**

```bash
week1_baseline/bin/ruby/check-paths
cd week1_baseline/python && ./run-tests && cd ../..
printf '/help\n/exit\n' | ./week1_baseline/bin/ruby/08_the_repl_loop
printf '/help\n/exit\n' | ./week1_baseline/bin/python/08_the_repl_loop
```

Expected: checker passes; `All iterations passed.` covering all nine steps 00–08; both REPLs banner, help, and exit cleanly.

- [ ] **Step 8: Commit**

```bash
git add week1_baseline/python/08_the_repl_loop week1_baseline/bin/python/08_the_repl_loop week1_baseline/python/README.md
git commit -m "python step 08: example, launcher, docs"
```

---

## Self-Review

**Spec coverage.** All six changes from `docs/superpowers/specs/2026-08-03-ruby-step-08-repl-fix-design.md` map to Task 1 steps 1a–1e and 2. The spec's Verification section maps to Task 1 steps 3–6. The spec's Delivery note (step 08 untracked) is Task 1 step 7. The Python port was a spec non-goal, later authorised by the user; Tasks 2–4 cover it and this plan supersedes that non-goal.

**Known gaps the implementer must close, not skip:**
- Task 2 steps 8 and 12 reference existing fixtures in `test_agent.py` and `test_client.py` that were not read while writing this plan. Read those files and match their established style rather than inventing new fixtures.
- Task 3 step 9's expected test count is arithmetic, not observed. Treat the actual number as correct if every test passes.
- Task 4 step 4's residual Ruby/Python banner difference is unknown until run. Whatever it is gets recorded in the README rather than papered over.
