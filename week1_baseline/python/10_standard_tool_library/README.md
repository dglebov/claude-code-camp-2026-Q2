# 10 · A Standard Tool Library (Python)

Python port of `week1_baseline/ruby/10_standard_tool_library`.

> **Step 09 is skipped in this tree** (`ITERATIONS.md` §09), so this port folds the 08→09 and
> 09→10 deltas at once. The directory numbering keeps the gap visible rather than renumbering.

## The one file that is not ported

Ruby's `Boukensha::Tools::Mud` — 480 lines, 27 tools — begins `require "mud_manager"`. There is
no way to load a Ruby gem from Python, and reimplementing it means writing a stateful telnet
client, an IAC stripper and a CircleMUD login state machine in a second language.

So it is not ported. **This tree reaches the MUD over MCP instead**, and that is the point rather
than a shortfall: it is exactly the problem
[`docs/plans/mud_manager/generic_interfacing.md`](../../../docs/plans/mud_manager/generic_interfacing.md)
was written about.

The consequence is that the Python tree lands in the shape `ITERATIONS.md` §10 describes as the
*target* — no built-in MUD module, gameplay purely over MCP — not by discipline but because the
shortcut does not exist here. The Python port is the proof the MCP layer works.

## What's new

### `boukensha.tools.file_system` — 6 tools

`pwd`, `list_directory`, `read_file`, `write_file`, `delete_file`, `search_files`. All paths are
relative to `working_dir`; absolute paths and `..` escapes return an error string rather than
raising, so the agent can react.

### `boukensha.tools.shell` — 1 tool

`run_command`, with a timeout and an optional `allowed_commands` list.

> **`allowed_commands` is advisory, not a security boundary — in both trees.** It checks only the
> first token, and commands run through a shell (mirroring Ruby, verified against the reference),
> so `git; rm -rf ~` passes a `["git"]` allow-list. `test_tools_shell.py` pins this deliberately.

### `boukensha.mcp.Client` and `boukensha.tools.mcp` — the MCP host

Loads tools from any MCP server over stdio. Neither contains a line of MUD- or
filesystem-specific code. Declare servers in `.boukensha/settings.yaml`:

```yaml
mcp_servers:
  - name: mud
    command: mud-manager
    args: ["--mcp"]
    required: false          # a failed start warns instead of killing the run
    env:
      MUD_HOST: localhost
      MUD_PORT: "4000"
      MUD_USERNAME: yourname
      MUD_PASSWORD: yourpassword
```

Annotated example: [`week1_baseline/mcp/settings.example.yaml`](../../mcp/settings.example.yaml).
The `mud-manager` gem must be installed and on `PATH` — see
[`week1_baseline/mcp/README.md`](../../mcp/README.md).

**No `prefix:` is needed here.** Ruby needs one because its built-in `Tools::Mud` already owns
`look`, `move` and `attack`. This tree has no built-ins to collide with, so MCP tools keep their
bare names — meaning **the two trees' tool names differ by design**.

### `Tool.required_keys()`

MCP tools carry a real JSON Schema `required` list, and optional parameters are common (`look`
takes an optional target). Previously every backend advertised *all* parameters as required.
`required_keys()` defaults to that old behaviour, so built-ins are unaffected, and honours an
explicit list when given.

### New `run` / `repl` keyword arguments

```python
boukensha.run(
    task="...",
    working_dir="/my/project",       # default: os.getcwd(); False disables the tool modules
    allowed_commands=["python3", "git"],
    shell_timeout=30,
)
```

## Differences from the Ruby original

- **No `tools/mud.py`**, no `mud:` keyword, no `mud_*` wiring on `run`/`repl` — see above.
- **MCP tools use bare names**, since there are no built-ins to collide with.
- **`Registry.tool` is a decorator**, so MCP tools — which have no `def` to decorate — are
  registered through its call form: `registry.tool(name, ...)(handler)`.
- **Path containment uses `os.path.abspath`, not `Path.resolve`.** Ruby's `File.expand_path`
  normalises without resolving symlinks; matching it keeps the trees consistent, and means a
  symlink inside the root pointing outside it is followed by both. `realpath` would be stricter
  and would make them disagree. Pinned by `test_a_symlink_pointing_outside_the_root_is_FOLLOWED`.
- **The MCP client leaves stderr inherited.** Reading a live child's stderr synchronously
  deadlocks in Python; server diagnostics go to the terminal instead.
- **Non-text MCP content is reported, not silently dropped** — the Ruby client discards it.
- **`env_file.py` stays.** Ruby moved to the `dotenv` gem in the skipped step 09.

## Run

```bash
./week1_baseline/bin/python/10_standard_tool_library
```

> **Makes billed API calls.** Needs `ANTHROPIC_API_KEY` in `.boukensha/.env`.

## Test

```bash
cd week1_baseline/python
uv run pytest 10_standard_tool_library
```

497 tests, all offline. The MCP client is driven by a scripted server over in-memory pipes, so
no subprocess or MUD is needed for the protocol tests.
