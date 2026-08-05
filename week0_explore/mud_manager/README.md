# MudManager

The MudManager has the following responsibilities:

- manages long-lived telnet sessions
- manages the multi-step process of logging back in
- provides generic primitives for MUD commands
- **owns those sessions in a daemon**, so short-lived clients don't have to
- **exposes them over MCP and a CLI**, so harnesses in any language can play

## Interfaces

A MUD session is stateful — login state, in-world state, and chatter arriving
between commands — so it must outlive any one client. That is what the daemon is
for. Everything else is a front-end onto it.

```sh
mud-manager daemon      # owns the sessions (auto-started by clients)
mud-manager --mcp       # MCP server over stdio, for agent hosts
mud-manager tools       # the 34-tool surface
mud-manager connect --user NAME --password PW
mud-manager tool look
mud-manager send "say hello"
mud-manager sessions
mud-manager stop
```

`MudManager::ToolTable` is the single source for the agent-facing surface: it
generates the MCP schema *and* dispatches into `Primitives`, so the command set
is defined once rather than transcribed per consumer.

See `week1_baseline/mcp/` for an offline end-to-end check and a Python client
demo.

## Build the Gem

From this directory:

```sh
gem build mud_manager.gemspec
gem install ./mud_manager-0.1.0.gem
```

Expected output:

```text
MudManager
```

## Uninstall

```sh
gem uninstall mud_manager
```

## Examples

Test the live session:

```sh
MUD_NAME=YourCharacterName MUD_PASSWORD=yourpassword ruby mud_manager/examples/live_session_test.rb
```

If you are already inside the `mud_manager` directory, run:

```sh
MUD_NAME=YourCharacterName MUD_PASSWORD=yourpassword ruby examples/live_session_test.rb
```
