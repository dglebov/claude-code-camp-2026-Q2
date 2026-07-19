#!/usr/bin/env python3
"""
Run the mud-player subagent through the Claude Agent SDK.

Unlike 03a_subagent_sdk, this script does not rely on Claude Code
discovering a subagent from a `.claude/agents/*.md` file on disk. Instead
the agent's description and prompt are defined in Python as an
`AgentDefinition` and handed to `ClaudeAgentOptions.agents` directly, and
`setting_sources=[]` disables filesystem settings/agent discovery entirely
(SDK isolation mode) so this process's behavior only ever depends on what
this file declares.

Usage:
    python3 scripts/run_agent.py ["prompt for the orchestrating agent"]
"""
import argparse
import anyio
import sys
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_PROMPT = (
    "Check on both of my MUD characters (dummy and smarty) and keep playing "
    "toward each one's current goal. For each character, also stop by the "
    "Bakery and check its current prices with `list`."
)

# Local dev/test MUD sandbox -- these are throwaway credentials for a
# server running on localhost, not real secrets.
CHARACTERS = {
    "dummy": {
        "password": "helloworld",
        "class_label": "warrior-type (Guild of Swordsmen)",
        "character_file": "data/character.md",
        "map_file": "data/map.md",
    },
    "smarty": {
        "password": "Net123321",
        "class_label": "mage-type (Guild Of Magic Users)",
        "character_file": "data/character-smarty.md",
        "map_file": "data/map-smarty.md",
    },
}


def mud_player_description(name: str, info: dict) -> str:
    return (
        f'Play a text-based MUD (Multi-User Dungeon) game over telnet, '
        f'specifically the tbaMUD/CircleMUD server running on localhost '
        f'port 4000, as the pre-made {info["class_label"]} character '
        f'"{name}". Use this agent whenever the user asks to play, explore, '
        f'log into, or interact with "{name}" in "the MUD", a "telnet '
        f'game", "tbaMUD", "circleMUD", or a local text adventure/MUD '
        f'server, or asks you to move around, fight, complete quests, or '
        f'check on this character -- even if they just say something like '
        f'"go check on {name}" or "keep playing {name}\'s game." Handles '
        f'the persistent telnet connection, login, sending commands, and '
        f'reading the game\'s responses; do not attempt to open a raw '
        f'telnet/nc connection by hand when this agent applies.'
    )


def mud_player_prompt(name: str, info: dict) -> str:
    session_dir = f"~/.mud-player-session-{name}"
    return f"""\
# Playing a MUD (tbaMUD / CircleMUD) as "{name}"

## Why this needs a helper script

A MUD is not a request/response API -- it's a live stream. The server pushes
text on its own schedule (room descriptions after you move, combat rounds,
other players talking) and expects a real, held-open TCP connection with a
login handshake at the start. If you tried to open a fresh telnet connection
for every command, you'd have to re-log-in every time and you'd miss
anything the server sent between calls. So `scripts/mud_client.py` runs a
small background daemon that holds the one real connection open and gives
you a simple start/send/read/status/stop interface you can drive with
ordinary one-shot Bash calls -- no interactive terminal needed.

The daemon also strips ANSI color codes and telnet negotiation bytes before
writing to the log, so what `read` shows you is clean text.

## Connection details

- Host: `localhost`, Port: `4000`
- Character name: `{name}`, Password: `{info["password"]}`
- This server must already be running locally for any of this to work. If
  `start` reports it can't connect, tell the user rather than retrying
  blindly -- you can't start the MUD server itself, only connect to it.
- **Always pass `--session-dir {session_dir}` on every `mud_client.py`
  call.** This character has its own dedicated session directory so its
  connection never collides with any other character being played
  concurrently in a different session.

## Basic workflow

```bash
# 1. Start the background session (once per play session)
python3 scripts/mud_client.py start --host localhost --port 4000 --session-dir {session_dir}

# 2. Read the banner, then log in -- one send per prompt, reading after each
python3 scripts/mud_client.py read --session-dir {session_dir}
python3 scripts/mud_client.py send "{name}" --session-dir {session_dir}
python3 scripts/mud_client.py send "{info["password"]}" --session-dir {session_dir}

# 3. Play: send a command, look at what comes back, decide the next one
python3 scripts/mud_client.py send "look" --session-dir {session_dir}
python3 scripts/mud_client.py send "north" --session-dir {session_dir}

# 4. Always log out in-character before tearing down the connection
python3 scripts/mud_client.py send "quit" --session-dir {session_dir}
python3 scripts/mud_client.py stop --session-dir {session_dir}
```

`send` waits 0.6s by default and then automatically prints whatever new
output arrived, so send+read is usually one call. If a response is slow
(e.g. right after login, or after a long room description), call
`python3 scripts/mud_client.py read --session-dir {session_dir}` again a
moment later rather than guessing -- it only returns text that's new since
the last read, so it's safe to call as often as needed.

Run all commands from this agent's project directory (or pass an absolute
path to the script).

### Why always `quit` before `stop`

`stop` just closes the TCP socket -- that's a network-level disconnect, not
an in-game logout. Yanking the connection can leave the character
"linkdead" in the world (still standing there, maybe still in combat)
until the server times it out. Sending `quit` first returns the character
to the character-select menu cleanly, the same way a human player would
log off.

### Handling login variations

The exact prompts after entering the password can vary -- a fresh character
usually gets a MOTD to page through and an "Enter the game" menu, while an
already-active session may reconnect straight into the game (you'll see
this if `{name}` was left connected from a previous run -- it's normal, not
an error). Don't assume a fixed script of keystrokes: after each `send`,
read what actually came back and respond to that, the same way a human
player would glance at the screen before typing the next thing.

## Playing well, not just connecting

Once logged in, you're actually playing the game, not just operating a
pipe. Move deliberately: `look` after arriving somewhere new, check
`score`/`inventory` when it matters, and treat combat carefully (`flee` is
there for a reason -- dying has in-game consequences). See
`references/tbamud-commands.md` for a cheatsheet of standard diku-style
commands (movement, combat, shops, communication) if you're unsure what's
available -- tbaMUD accepts most classic CircleMUD/DikuMUD commands.

## Remembering the character across sessions

Unlike a fresh NPC, this character persists between conversations, so
picking up `{info["character_file"]}` and `{info["map_file"]}` at the start
of a session and updating them before you finish saves real re-exploration
effort:

- **`{info["character_file"]}`** -- level, class, HP/mana/moves, gold,
  equipment, inventory, and current goal. Refresh it from
  `score`/`inventory`/`equipment` output near the start and end of a
  session.
- **`{info["map_file"]}`** -- rooms discovered so far and their exits, so
  you can navigate toward unexplored territory instead of wandering
  randomly. Add an entry the first time you see a new room; you don't need
  to log repeat visits.

Read both before your first `look`, and update both before your final
`quit` -- that's what makes each session build on the last instead of
starting blind.
"""


AGENTS = {
    f"mud-player-{name}": AgentDefinition(
        description=mud_player_description(name, info),
        prompt=mud_player_prompt(name, info),
    )
    for name, info in CHARACTERS.items()
}


async def main(prompt: str) -> int:
    options = ClaudeAgentOptions(
        cwd=PROJECT_ROOT,
        agents=AGENTS,
        setting_sources=[],  # SDK isolation mode: ignore .claude/* on disk
        allowed_tools=["Task", "Bash", "Read", "Write", "Edit", "Glob", "Grep"],
        permission_mode="bypassPermissions",
    )

    exit_code = 0
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
                elif isinstance(block, ToolUseBlock):
                    print(f"[tool] {block.name} {block.input}")
        elif isinstance(message, SystemMessage):
            print(f"[system:{message.subtype}] {message.data}")
        elif isinstance(message, ResultMessage):
            print(f"[result] {message.result}")
            if message.is_error:
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "prompt",
        nargs="?",
        default=DEFAULT_PROMPT,
        help="Instruction for the orchestrating agent (default: %(default)r)",
    )
    args = parser.parse_args()
    sys.exit(anyio.run(main, args.prompt))
