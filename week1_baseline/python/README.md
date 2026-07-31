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
uv run pytest                                 # test all iterations
uv run ruff check .                           # lint
```

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

This is what lets twelve directories each define `boukensha` without colliding.

---

## Iterations

| Step | Directory | Launcher |
|------|-----------|----------|
| 00 · Configuration | `00_config/` | `week1_baseline/bin/python/00_config` |

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
