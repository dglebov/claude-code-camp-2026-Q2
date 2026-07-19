# World map notes (smarty session)

A running log of rooms visited by the "smarty" character, so navigation
gets faster each session instead of re-exploring blindly. This is the same
game world as the "dummy" character's map.md, so overlapping town-hub rooms
match exactly, but this file focuses on the mage-guild path smarty actually
walked (rooms already fully documented in map.md are noted briefly with a
cross-reference rather than re-described in full).

Format:
```
## <Room name>
Exits: <direction -> room name or "unexplored">
Notable: <shops, NPCs, mobs, items, dangers>
```

## The Temple Of Midgaard
Exits: n -> By The Temple Altar, e -> Midgaard Donation Room, s -> Temple
Square, w -> The Reading Room, d -> Temple Square (shortcut)
Notable: starting room on login for smarty. ATM here. Matches map.md
exactly (see dummy's map.md for full detail on this and the Temple Square /
Market Square hub rooms below).

## Temple Square
Exits: n -> Temple Of Midgaard, e -> Grunting Boar Inn, s -> Market Square,
w -> Entrance To The Clerics' Guild
Notable: large fountain. Matches map.md.

## Market Square
Exits: n -> Temple Square, s -> Common Square, e -> Main Street (general
store/pet shop), w -> Main Street (bakery/armory)
Notable: central hub with a large statue. Matches map.md.

## Main Street (bakery/armory)
Exits: n -> The Bakery, s -> The Armory, e -> Market Square, w -> Main
Street (magic guild one)
Notable: hub connecting bakery/armory to the rest of Midgaard. Matches
map.md.

## Main Street (west end, magic guild)
Exits: n -> Magic Shop (unexplored), s -> Entrance To The Mages' Guild, e ->
Main Street (bakery/armory), w -> city gate (unexplored)
Notable: a Peacekeeper and two beastly fidos present here. South exit is
**smarty's home guild entrance**. **DANGER: do NOT attack the fidos here —
the Peacekeeper "jumps to the aid" of the fido and the guards killed smarty
(level 1, 14 HP) in one fight on 2026-07-19.** Any mob in a guarded room is
off-limits at this level.

## The Bakery
Exits: s -> Main Street (bakery/armory)
Notable: shop run by "the baker". `list` prices (2026-07-19): a danish
pastry = 7, a bread = 14, a waybread = 70 (all Unlimited stock). Reached
via n from Main Street (bakery/armory).

## The Midgaard Donation Room
Exits: w -> The Temple Of Midgaard
Notable: "a very kind and caring soul" NPC says 'get some clothes on! Here,
I will help.' but **gives NO items** — it is flavor-only in this MUD
config. No starter gear obtainable here (confirmed 2026-07-19, checked
inventory + floor multiple times, including right after a "Welcome to the
realm" broadcast). Reached via e from The Temple Of Midgaard. This is also
where smarty respawns' route back... (respawn point on death = The Temple
Of Midgaard, one room west).

## The Entrance To The Mages' Guild
Exits: n -> Main Street (west end, magic guild), s -> The Mages' Bar
Notable: small, poorly lit entrance hall. An ATM here. Guarded by a
sorcerer; also a Peacekeeper, a janitor, and a cityguard present — the
sorcerer guarding it is a strong signal this is the mage guild.

## The Mages' Bar
Exits: n -> The Entrance To The Mages' Guild, e -> The Mages' Laboratory
Notable: a bulletin board and a waiter NPC. Weird mystical/illusory
furniture and floating images described in the room text.

## The Mages' Laboratory
Exits: w -> The Mages' Bar
Notable: **the guildmaster is here** ("Your guildmaster is studying a
spellbook while preparing to cast a spell") — this is where `practice
<spell>` works for smarty. Practiced `magic missile` twice here on
2026-07-19, proficiency went not-learned -> average -> superb. 1 practice
session remains unused. Dead-end room (only exit is back west) — no further
rooms explored beyond this point this session.
