# tbaMUD / CircleMUD command cheatsheet

tbaMUD is a modern fork of CircleMUD (itself derived from DikuMUD), so most
"diku-style" commands below work unmodified. Server-specific commands (areas,
custom quests, staff commands) won't be listed here — use `help <topic>` or
`commands` / `socials` in-game to discover those live.

## Movement
- `north` / `n`, `south` / `s`, `east` / `e`, `west` / `w`, `up` / `u`, `down` / `d`
  (also intercardinal on some areas: `ne`, `nw`, `se`, `sw`)
- `look` / `l` — redescribe the current room (do this after every move)
- `look <direction>` — peek through an exit without moving
- `exits` — list obvious exits from the current room
- `enter <portal/building>` — enter a special exit

## Perception & info
- `score` / `sc` — character stats: HP/mana/moves, level, XP, alignment, gold
- `inventory` / `i` — items you're carrying
- `equipment` / `eq` — items you're wearing/wielding
- `who` — list of players currently online
- `time` — in-game time
- `weather` — current weather (outdoor areas)

## Interacting with objects/people
- `get <item>` / `get <item> <container>` — pick something up
- `drop <item>`
- `put <item> <container>`
- `wear <item>`, `wield <weapon>`, `remove <item>`
- `give <item> <person>`
- `look <item/person>` — examine
- `open <door/container>`, `close`, `lock`, `unlock` (may need a key)

## Communication
- `say <message>` — talk to the room
- `tell <person> <message>` — private message
- `emote <action>` — roleplay action text
- social commands (e.g. `smile`, `wave`) — see `socials` for the full list

## Combat
- `kill <target>` / `k <target>` — initiate combat
- `flee` — attempt to escape combat
- `consider <target>` — gauge how dangerous a target is before engaging
- class-specific commands (`cast <spell> <target>`, `bash`, `kick`, etc.)
  vary by class — check `spells`, `skills`, or `practice` for what your
  character actually knows

## Shops & economy
- `list` — see a shopkeeper's wares (while in a shop room)
- `buy <item>`, `sell <item>`
- `value <item>` — check what a shop would pay for something

## Rest & recovery
- `rest`, `sleep`, `wake`, `stand` — resting/sleeping recovers HP/mana/moves
  faster than standing; you can't act (move, fight) while resting or asleep

## Session / meta
- `save` — force-save your character (also happens periodically and on quit)
- `quit` — log out cleanly, returning to the character menu (always do this
  before ending a play session — see SKILL.md for why)
- `help <topic>` — in-game help system; `help` alone lists categories

## Reading room output
Typical room text has three parts, in this order — the connection script
already strips ANSI color codes and telnet control bytes, so what you'll see
is plain text:
1. Room name (line 1)
2. Room description (prose)
3. `[ Exits: n s e ]` or similar
4. Anything else present: other characters, visible items, NPC action text

The status line after a command (e.g. `24H 100M 79V (news) (motd) >`) shows
current HP/mana/moves and is the prompt — a new one appears after every
server response, so seeing it means the server has finished responding for
now and it's safe to send the next command.
