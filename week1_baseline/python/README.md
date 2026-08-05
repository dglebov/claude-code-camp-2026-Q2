# Boukensha — Python

Python port of the `week1_baseline/ruby` iterations. The Ruby tree stays the reference
implementation; this tree mirrors it 1:1 so the two stay diffable step by step.

---

## Environment setup — do this first

There is **one shared virtualenv for all week1 Python iterations**, living here at
`week1_baseline/python/.venv`. Future steps (`01_struct_skeleton`, `02_the_registry`, …) reuse
it — you do not create a new environment per step.

Requires [uv](https://docs.astral.sh/uv/). Install it with `brew install uv` if you don't have it.

```bash
cd week1_baseline/python
uv sync
```

That creates `.venv` (CPython 3.14, fetched automatically by uv) and installs the dependencies.
Everything below assumes it exists.

To run anything, prefix with `uv run` from this directory:

```bash
uv run python 00_config/examples/example.py   # run an iteration's example
uv run pytest 00_config                       # test one iteration
./run-tests                                   # test all iterations
uv run ruff check .                           # lint
```

> **Do not run a bare `uv run pytest` across iterations** — it fails during collection. Every
> iteration ships a package literally named `boukensha`, and `sys.modules` is keyed by name, so
> only the first one imported would ever be used; duplicate test-module basenames
> (`test_config.py` in every step) collide the same way. `./run-tests` gives each iteration its
> own pytest process, which is the only thing that actually works. `uv run pytest <step>` is
> fine — that's a single iteration.

### Dependencies

Deliberately minimal, matching the Ruby side's "use the standard library as much as possible"
constraint:

| Package | Why |
|---------|-----|
| `pyyaml` | Ruby gets YAML from its stdlib; Python does not. Unavoidable. |
| `pytest` (dev) | Test runner. |
| `ruff` (dev) | Lint/format, `line-length = 120`. |

Notably **not** used: `python-dotenv`. The Ruby side takes `dotenv` as its one exception, but on
the Python side a ~40-line stdlib loader (`boukensha/env_file.py`) covers the same ground, so
PyYAML stays the only runtime dependency.

### How imports work without installing anything

Every iteration ships its own package literally named `boukensha`. They are never installed —
`uv sync` builds a deps-only environment (`[tool.uv] package = false`). Each iteration puts its
own root on `sys.path`:

- `examples/example.py` does it explicitly, mirroring Ruby's `require_relative "../lib/boukensha"`
- `conftest.py` does it for pytest

This is what lets twelve directories each define `boukensha` without colliding — **as long as
only one iteration is loaded per process.** Two different `boukensha` packages cannot coexist in
one interpreter, which is why `./run-tests` shells out per iteration rather than running a single
pytest session.

---

## Iterations

| Step | Directory | Launcher |
|------|-----------|----------|
| 00 · Configuration | `00_config/` | `week1_baseline/bin/python/00_config` |
| 01 · Struct Skeleton | `01_struct_skeleton/` | `week1_baseline/bin/python/01_struct_skeleton` |
| 02 · The Tool Registry | `02_the_registry/` | `week1_baseline/bin/python/02_the_registry` |
| 03 · The Prompt Builder | `03_prompt_builder/` | `week1_baseline/bin/python/03_prompt_builder` |
| 04 · The API Client | `04_api_client/` | `week1_baseline/bin/python/04_api_client` |
| 05 · The Agent Loop | `05_agent_loop/` | `week1_baseline/bin/python/05_agent_loop` |
| 06 · The Logger | `06_the_logger/` | `week1_baseline/bin/python/06_the_logger` |
| 07 · The Run DSL | `07_the_run_dsl/` | `week1_baseline/bin/python/07_the_run_dsl` |
| 08 · The REPL Loop | `08_the_repl_loop/` | `week1_baseline/bin/python/08_the_repl_loop` |
| 10 · A Standard Tool Library | `10_standard_tool_library/` | `week1_baseline/bin/python/10_standard_tool_library` |

Step 09 (the global executable / gem) is skipped in this tree — see `ITERATIONS.md` §09 — so the
numbering jumps from 08 to 10 to stay aligned with the Ruby steps.

Launchers live in `week1_baseline/bin/python/`, alongside their Ruby counterparts in
`week1_baseline/bin/ruby/`. They can be run from anywhere:

```bash
./week1_baseline/bin/python/00_config    # python
./week1_baseline/bin/ruby/00_config      # ruby, for comparison
```

## Verifying a port

Each step's Python output must match its Ruby counterpart exactly:

```bash
diff <(./week1_baseline/bin/ruby/00_config) <(./week1_baseline/bin/python/00_config)
```

Silence means parity.

**Steps 04–07 are the exceptions.** All make real API calls, and the model's reply differs
between runs, so a plain `diff` always reports differences. Compare the built *payload* instead —
it is deterministic, and the comparison is byte-for-byte and free. Step 06 also compares its
session log structurally (phase sequence and key vocabulary) and its header block byte-for-byte.
See [`04_api_client/README.md`](04_api_client/README.md),
[`05_agent_loop/README.md`](05_agent_loop/README.md) and
[`06_the_logger/README.md`](06_the_logger/README.md) and
[`07_the_run_dsl/README.md`](07_the_run_dsl/README.md). Step 07 additionally diverges by one
line of stdout by design — its header names the API, and that name differs by language.

**Step 08 is interactive, and diffs clean.** Its launcher reads from stdin, so drive both trees
with the same keystrokes rather than running them bare. Every built-in command is handled before
the agent runs, so this needs no API key and makes no billed call:

```bash
diff <(printf '/help\n/exit\n' | ./week1_baseline/bin/ruby/08_the_repl_loop) \
     <(printf '/help\n/exit\n' | ./week1_baseline/bin/python/08_the_repl_loop)
```

Byte-for-byte identical, banner included — the first whole-run parity since step 03. See
[`08_the_repl_loop/README.md`](08_the_repl_loop/README.md).

**Step 10 does not diff against Ruby, and that is by design.** The Ruby tree registers 27 MUD
tools from a built-in `Tools::Mud` module; this tree cannot — it wraps a Ruby gem — so it reaches
the MUD over MCP instead. Two consequences:

- Ruby prefixes its MCP tools (`mud_look`) to avoid colliding with its built-ins; Python has no
  built-ins to collide with and uses bare names (`look`). **Tool names differ deliberately.**
- Ruby's banner carries a `mud:` line fed by its `mud:` options hash; Python has none.

What *is* comparable is the MCP layer itself, and it is verified end to end: the Python host
drives the same `mud-manager --mcp` server the Ruby host uses, against the same stub MUD, with
schemas and validation intact. See [`10_standard_tool_library/README.md`](10_standard_tool_library/README.md)
and [`../mcp/README.md`](../mcp/README.md).
