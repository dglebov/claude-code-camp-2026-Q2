# 02 · The Tool Registry (Python)

Python port of `week1_baseline/ruby/02_the_registry`.

> Requires the shared environment. If you haven't run `uv sync` in `week1_baseline/python`, do
> that first — see [`../README.md`](../README.md).

The Tool Registry is how Boukensha manages what the agent can do. It has two jobs: **storing**
tools and **dispatching** them when asked.

## How it works

The agent never calls a tool directly. It emits a structured request — a name and a dict of
arguments — and the Registry looks the tool up and runs it.

```
Agent:    "call move with direction='north'"
Registry: looks up "move" in the tool table
Registry: calls the block with the provided args
Registry: "here's the result"
```

## `Registry`

| Method | Description |
|---|---|
| `Registry(context)` | Holds a reference to the Context. Registration writes through to it. |
| `tool(name, *, description, parameters=None)` | Returns a decorator that registers the wrapped function as a tool |
| `dispatch(name, args=None)` | Looks up a tool by name and calls it with the provided args |

Tools are still stored on the **Context**, not on the Registry — the Registry only writes to it.
That mirrors the Ruby original; `week1_baseline/ITERATIONS.md` notes the arrangement is something
that ought to move onto the Registry eventually.

## `UnknownToolError`

Raised when `dispatch` is called with a name that has no registered tool. A harness needs explicit
error boundaries — an unrecognised tool name should never silently fail.

```
UnknownToolError: No tool registered as 'flee'
```

The boundary is about the *name*. A bad argument list fails inside the block itself, as a
`TypeError`.

## Registering a tool

Ruby passes the implementation as a trailing block. Python has no block syntax, so `tool` returns
a decorator and the decorated function is the block:

```python
@registry.tool(
    "move",
    description="Move the player in a direction (north, south, east, west, up, down)",
    parameters={"direction": {"type": "string"}},
)
def move(*, direction):
    return f"You move {direction} into a torch-lit corridor."
```

The tools are written keyword-only (`*, direction`) because `dispatch` calls them with `**args`.
This matches Ruby's `do |direction:|`, which likewise requires the keyword and rejects extras.

## Code map

| File | Purpose | Ruby original |
|------|---------|---------------|
| `boukensha/registry.py` | `Registry` — registers tools and dispatches calls | `lib/boukensha/registry.rb` |
| `boukensha/errors.py` | `UnknownToolError` | `lib/boukensha/errors.rb` |
| `boukensha/tool.py`, `message.py`, `context.py` | carried forward from step 01, unchanged | `lib/boukensha/` |
| `boukensha/config.py`, `tasks/`, `env_file.py` | carried forward from step 01, unchanged | `lib/boukensha/` |

Only two files are new. The Ruby step-02 tree is byte-identical to step 01 apart from
`registry.rb`, `errors.rb`, the two extra requires in `lib/boukensha.rb`, and the example — so the
Python carry-forward is byte-identical too.

## Differences from the Ruby original

| Ruby | Python | Why |
|------|--------|-----|
| `def tool(..., &block)` + `do ... end` | decorator returning the function | Python has no block syntax. Ruby's `tool` returns the `Tool`; this returns a decorator, and the name stays bound to the function. |
| `args.transform_keys(&:to_sym)` | nothing | Ruby blocks want symbol keys but the API sends strings. Python keyword arguments *are* strings, so the translation is a no-op. The seam is kept and commented — every tool call passes through it. |
| `class UnknownToolError < StandardError` | `class UnknownToolError(Exception)` | `StandardError` is Ruby's rescuable-by-default tier. `BaseException` would sit alongside `KeyboardInterrupt`. |
| `parameters: {}` / `args = {}` | `parameters=None` / `args=None` | Ruby allocates a fresh hash per call; a Python default is evaluated once at definition time and would be shared. |
| `name.to_s` | `str(name)` | So `dispatch(:move)` and `dispatch("move")` hit the same entry. |
| `e.message` | `{e}` | `str()` on a single-argument exception yields exactly the message. |

Also worth noting: Ruby's `to_sym` accepts any string, while Python's `**` rejects a key that is
not a valid identifier unless the callable takes `**kwargs`. Not reachable from this example.

## Run

```bash
./week1_baseline/bin/python/02_the_registry
```

Expected output:

```
=== BOUKENSHA Step 2: Tool Registry ===

Config:  #<Boukensha::Config dir=/Users/you/Sites/Claude-Code-Camp/.boukensha tasks=player>
Context: #<Context task=player turns=0 tools=2>
Tools:
  #<Tool name=move description=Move the player in a direction (north, so params=[:direction]>
  #<Tool name=shout description=Shout a message so everyone in the zone c params=[:message]>

Dispatching 'shout' with message='dragon spotted'...
Result: DRAGON SPOTTED

Dispatching 'move' with direction='north'...
Result: You move north into a torch-lit corridor.

UnknownToolError caught: No tool registered as 'flee'
```

Both `description=` values stop mid-word: Ruby's `str[0..40]` is an inclusive 41-character range,
which `boukensha/tool.py` reproduces. `params=[:direction]` is Ruby symbol-array syntax, likewise
reproduced. `turns=0` because this example adds no messages.

Verify parity against Ruby:

```bash
diff <(./week1_baseline/bin/ruby/02_the_registry) <(./week1_baseline/bin/python/02_the_registry)
```

## Test

```bash
cd week1_baseline/python
uv run pytest 02_the_registry
```
