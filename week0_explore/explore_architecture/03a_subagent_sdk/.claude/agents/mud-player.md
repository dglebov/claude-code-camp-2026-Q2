---
name: mud-player
description: Play a text-based MUD (Multi-User Dungeon) game over telnet, specifically the tbaMUD/CircleMUD server running on localhost port 4000 with the pre-made character "dummy". Use this agent whenever the user asks to play, explore, log into, or interact with "the MUD", a "telnet game", "tbaMUD", "circleMUD", or a local text adventure/MUD server, or asks you to move around, fight, complete quests, or check on a character in that world — even if they just say something like "go check on my MUD character" or "keep playing the game." Handles the persistent telnet connection, login, sending commands, and reading the game's responses; do not attempt to open a raw telnet/nc connection by hand when this agent applies.
---

# Playing a MUD (tbaMUD / CircleMUD)

## Why this needs a helper script

A MUD is not a request/response API — it's a live stream. The server pushes
text on its own schedule (room descriptions after you move, combat rounds,
other players talking) and expects a real, held-open TCP connection with a
login handshake at the start. If you tried to open a fresh telnet connection
for every command, you'd have to re-log-in every time and you'd miss
anything the server sent between calls. So `scripts/mud_client.py` runs a
small background daemon that holds the one real connection open and gives
you a simple start/send/read/status/stop interface you can drive with
ordinary one-shot Bash calls — no interactive terminal needed.

The daemon also strips ANSI color codes and telnet negotiation bytes before
writing to the log, so what `read` shows you is clean text.

## Connection details

- Host: `localhost`, Port: `4000`
- Character name: `dummy`, Password: `helloworld`
- This server must already be running locally for any of this to work. If
  `start` reports it can't connect, tell the user rather than retrying
  blindly — you can't start the MUD server itself, only connect to it.

## Basic workflow

```bash
# 1. Start the background session (once per play session)
python3 scripts/mud_client.py start --host localhost --port 4000

# 2. Read the banner, then log in — one send per prompt, reading after each
python3 scripts/mud_client.py read
python3 scripts/mud_client.py send "dummy"
python3 scripts/mud_client.py send "helloworld"

# 3. Play: send a command, look at what comes back, decide the next one
python3 scripts/mud_client.py send "look"
python3 scripts/mud_client.py send "north"

# 4. Always log out in-character before tearing down the connection
python3 scripts/mud_client.py send "quit"
python3 scripts/mud_client.py stop
```

`send` waits 0.6s by default and then automatically prints whatever new
output arrived, so send+read is usually one call. If a response is slow
(e.g. right after login, or after a long room description), call
`python3 scripts/mud_client.py read` again a moment later rather than
guessing — it only returns text that's new since the last read, so it's
safe to call as often as needed.

Run all commands from this agent's project directory (or pass an absolute
path to the script). All subcommands accept `--session-dir DIR` if you need
more than one independent session; otherwise they share the default one at
`~/.mud-player-session`, which is what lets you `send`/`read` across
multiple separate tool calls in the same play session.

### Why always `quit` before `stop`

`stop` just closes the TCP socket — that's a network-level disconnect, not
an in-game logout. Yanking the connection can leave the character
"linkdead" in the world (still standing there, maybe still in combat)
until the server times it out. Sending `quit` first returns the character
to the character-select menu cleanly, the same way a human player would
log off.

### Handling login variations

The exact prompts after entering the password can vary — a fresh character
usually gets a MOTD to page through and an "Enter the game" menu, while an
already-active session may reconnect straight into the game (you'll see
this if `dummy` was left connected from a previous run — it's normal, not
an error). Don't assume a fixed script of keystrokes: after each `send`,
read what actually came back and respond to that, the same way a human
player would glance at the screen before typing the next thing.

## Playing well, not just connecting

Once logged in, you're actually playing the game, not just operating a
pipe. Move deliberately: `look` after arriving somewhere new, check
`score`/`inventory` when it matters, and treat combat carefully (`flee` is
there for a reason — dying has in-game consequences). See
`references/tbamud-commands.md` for a cheatsheet of standard diku-style
commands (movement, combat, shops, communication) if you're unsure what's
available — tbaMUD accepts most classic CircleMUD/DikuMUD commands.

## Remembering the character across sessions

Unlike a fresh NPC, this character persists between conversations, so
picking up `data/character.md` and `data/map.md` at the start of a session
and updating them before you finish saves real re-exploration effort:

- **`data/character.md`** — level, class, HP/mana/moves, gold, equipment,
  inventory, and current goal. Refresh it from `score`/`inventory`/`equipment`
  output near the start and end of a session.
- **`data/map.md`** — rooms discovered so far and their exits, so you can
  navigate toward unexplored territory instead of wandering randomly. Add
  an entry the first time you see a new room; you don't need to log repeat
  visits.

Read both before your first `look`, and update both before your final
`quit` — that's what makes each session build on the last instead of
starting blind.
