# Step 10 — A Standard Tool Library

Boukensha ships built-in tool modules and becomes an **MCP host**. Instead of manually registering tools, a real coding harness gives the agent a standard library of capabilities out of the box — some built in, and any number more declared in config.

## What's new

### `Boukensha::Tools::FileSystem`

The evolution of step 9's `WorkingDirectory` — same five tools plus one new one. Registers automatically when `working_dir:` is set:

| Tool | Description |
|------|-------------|
| `pwd` | Return the working directory |
| `list_directory` | List files at a path (default `.`) |
| `read_file` | Read a file's contents |
| `write_file` | Write (or create) a file |
| `delete_file` | Delete a file |
| `search_files` | **New** — grep for a regex pattern across the working tree, returns `path:line:content` matches |

All paths are **relative to the working directory**. Absolute paths and `..` traversals that escape the root are rejected with an error string.

### `Boukensha::Tools::Shell`

New module. Registers automatically when `working_dir:` is set:

| Tool | Description |
|------|-------------|
| `run_command` | Run a shell command inside the working directory |

Commands run with a configurable timeout and an optional allow-list of permitted executables.

### `Boukensha::Tools::Mud`

Registers 27 CircleMUD gameplay tools against a live connection, wrapping the
`mud_manager` gem directly. Enabled when `mud:` options are present (from
`settings.yaml`'s `mud:` block by default); pass `mud: false` to skip it.

> Superseded by the MCP path below, which reaches the same MUD through a
> language-neutral server instead of a Ruby-only module. Kept so nothing that
> works today breaks — see `docs/plans/mud_manager/implementation.md` §9.

### `Boukensha::Mcp::Client` and `Boukensha::Tools::Mcp` — the MCP host

Boukensha can now load tools from any [MCP](https://modelcontextprotocol.io)
server over stdio. Neither file contains a line of MUD- or filesystem-specific
code: a server is a `command`, `args` and `env`, and whatever tools it advertises
are registered into the same `Registry` the built-ins use.

Declare servers in `.boukensha/settings.yaml` — **adding a capability is a config
edit, not a code change**:

```yaml
mcp_servers:
  - name: mud
    command: mud-manager
    args: ["--mcp"]
    prefix: mud          # namespaces tools client-side: mud_look, mud_move …
    required: false      # a failed start warns instead of killing the run
    env:
      MUD_HOST: localhost
      MUD_PORT: "4000"
      MUD_USERNAME: yourname
      MUD_PASSWORD: yourpassword
```

A full annotated example is in
[`week1_baseline/mcp/settings.example.yaml`](../../mcp/settings.example.yaml).

**Name collisions raise.** `Tools::Mud` already registers `look`, `move` and
`attack`, so loading the MUD server unprefixed would clash. Either set
`prefix:` as above, or pass `mud: false` to drop the built-ins. `Tools::Mcp`
refuses to let one server silently shadow another, because a shadowed tool fails
as *the wrong thing happening in-game*, which is nearly impossible to trace back.

### `Tool#required_keys`

Tools discovered over MCP carry a real JSON Schema `required` list, and optional
parameters are common (`look` takes an optional target). Previously every
backend advertised *all* parameters as required. `Tool#required_keys` defaults to
that old behaviour, so built-ins are unaffected, and honours an explicit list
when one is given.

### New `Boukensha.run` / `Boukensha.repl` keyword arguments

```ruby
Boukensha.run(
  task:             "...",
  working_dir:      "/my/project",
  allowed_commands: ["ruby", "git", "bundle"],  # nil = allow all (default)
  shell_timeout:    30                           # seconds, default 30
)
```

`allowed_commands: nil` permits any executable. Pass an explicit list to lock the agent down:

```ruby
# Only allow ruby and git — rm, curl, etc. will be rejected
Boukensha.run(task: "...", allowed_commands: ["ruby", "git"])
```

### Direct registration

Both modules can be registered manually if you need finer control:

```ruby
Boukensha::Tools::FileSystem.register(registry, working_dir: "/my/project")
Boukensha::Tools::Shell.register(registry, working_dir: "/my/project",
                              timeout: 10, allowed_commands: ["ruby"])
```

## Run the demo

```sh
# from the repo, no install needed — runs from source
./week1_baseline/bin/ruby/10_standard_tool_library

# or directly
bundle exec ruby examples/example.rb
```

> **Makes billed API calls** and plays the MUD — `examples/example.rb` is a
> one-shot `Boukensha.run` demo, not a REPL.

## Install globally

The launcher above runs from source, so it always reflects your edits. Install
only if you want the global `boukensha` command to be this step:

```sh
gem build boukensha.gemspec
gem install ./boukensha-0.10.0.gem
```

It replaces any previously installed `boukensha` — same gem name, one binary.
Other steps stay reachable regardless:

```sh
BOUKENSHA_PATH=/path/to/week1_baseline/ruby/09_global_executable boukensha
```

**MCP needs this step installed.** Steps 09 and earlier ship no `mcp/` or
`tools/` directories, so a globally installed 0.9.0 cannot host an MCP server no
matter how `mcp_servers:` is configured.

`mcp_servers:` entries using `command: mud-manager` also need that gem installed
and on `PATH` — see [`week1_baseline/mcp/README.md`](../../mcp/README.md).
