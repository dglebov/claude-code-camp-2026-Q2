# World map notes

A running log of rooms visited, so navigation gets faster each session
instead of re-exploring blindly. One entry per distinct room is enough —
you don't need to log every single visit, just add a room the first time
you see it and update it if you learn something new (a locked exit turns
out to be a shop, a mob spawns there, etc.).

Format:
```
## <Room name>
Exits: <direction -> room name or "unexplored">
Notable: <shops, NPCs, mobs, items, dangers>
```

## The Bakery
Exits: s -> Main Street (bakery/armory one)
Notable: starting room on login; a baker NPC and a small sign are present.
Sign reads: "buy" purchases bread/pastry, "list" shows price and sort of
bread. Confirmed menu via `list`: 1) A danish pastry - 7 coins,
2) A bread - 14 coins, 3) A waybread - 70 coins (all "Unlimited" stock).

## Main Street (bakery/armory)
Exits: n -> The Bakery, s -> The Armory, e -> Market Square, w -> Main Street (magic guild one)
Notable: hub connecting the bakery and armory to the rest of Midgaard.

## The Armory
Exits: n -> Main Street (bakery/armory)
Notable: sells armor. A cityguard, a Peacekeeper, an armorer, and an oozing
green gelatinous blob (mob) are present.

## Market Square
Exits: n -> Temple Square, s -> Common Square, e -> Main Street (general store/pet shop), w -> Main Street (bakery/armory)
Notable: central hub with a large statue. Roads to all four guild-adjacent
areas of the city radiate from here.

## Temple Square
Exits: n -> Temple Of Midgaard, e -> Grunting Boar Inn (entrance hall), s -> Market Square, w -> Entrance To The Clerics' Guild
Notable: large fountain — confirmed FREE and repeatable water source via
`drink fountain` (2026-07-19), fully clears thirst ("You don't feel
thirsty any more."), no gold needed, enchanted so it never runs dry.
Clerics' Guild entrance to the west (guarded by a knight templar);
Grunting Boar Inn (a tavern, not our guild) to the east.

## Entrance To The Clerics' Guild
Exits: n -> Bar (of clerics, unexplored beyond), e -> Temple Square
Notable: NOT our guild (character is warrior-type). Guarded by a knight
templar; has an ATM.

## The Temple Of Midgaard
Exits: n -> By The Temple Altar, e -> Midgaard Donation Room, s -> Temple Square, w -> The Reading Room, d -> Temple Square (shortcut)
Notable: ATM here. Central temple hall with wall paintings.

## By The Temple Altar
Exits: n -> Behind The Temple Altar, s -> The Temple Of Midgaard
Notable: statue of Odin.

## Behind The Temple Altar
Exits: n -> The Great Field Of Midgaard, s -> By The Temple Altar
Notable: dirt path leading out of the city toward the Dragonhelm Mountains.
Nothing interactable found.

## The Great Field Of Midgaard
Exits: n -> unexplored (further countryside), s -> Behind The Temple Altar
Notable: open countryside — grass and oak trees, but pure flavor text (no
`look tree`/edible items found, 2026-07-19). Did not push further north
into unmapped wilderness solo at level 1. City visible to the south.

## The Reading Room
Exits: e -> The Temple Of Midgaard
Notable: a bulletin board, a "teleporter" device, and an overpriced
saleswoman NPC.

## The Midgaard Donation Room
Exits: w -> The Temple Of Midgaard
Notable: a kind/caring soul NPC here gave the character a full set of
starter armor and weapons unprompted (candle, rings, gorgets, breast plate,
cap, leggings, boots, gloves, sleeves, shield, cape, belt, wristguards,
small sword, metal staff) — worth visiting early on a fresh character.
Re-checked 2026-07-19 while hungry: no free food from her — `ask soul about
food` got no useful reply and nothing appeared in inventory. The gear gift
seems to be a one-time/early-game event, not a repeatable food source.

## Grunting Boar Inn - Entrance Hall
Exits: n -> Post Office, e -> Bar (unexplored beyond), w -> Temple Square, u -> reception (unexplored beyond)
Notable: an inn, not a guild.

## Post Office
Exits: s -> Grunting Boar Inn - Entrance Hall
Notable: head postmaster NPC, a sign on the wall.

## Common Square
Exits: n -> Market Square, e -> The Dark Alley, s -> The Dump, w -> Poor Alley (eastern end)
Notable: several beastly fido mobs scavenging garbage here. Checked
2026-07-19 for free food: the "garbage" is flavor text only, not a
lootable/edible object (`look garbage` -> "You do not see that here.").
**DANGER (2026-07-19): a cityguard here ASSISTS the fidos.** Attacked a fido
and "The cityguard jumps to the aid of the beastly fido!" — the guard hits
for ~9 damage (over a third of a level-1 HP bar). Do NOT fight fidos in any
room containing a cityguard/Peacekeeper/knight. Fight them only in
guard-free rooms (see Main Street weapon-shop/Swordsmen entry).

## The Dump
Exits: n -> Common Square, d -> sewer system (unexplored)
Notable: entrance to the sewers. Checked 2026-07-19: no free food item
here either, same as Common Square.

## Poor Alley (eastern end)
Exits: e -> Common Square, s -> Grubby Inn (unexplored), w -> Poor Alley (continues)
Notable: a Peacekeeper and beastly fidos present.

## The Dark Alley
Exits: w -> Common Square, s -> Guild Of Thieves (unexplored — not our guild), e -> Dark Alley At The Levee
Notable: mercenary NPCs waiting for jobs.

## Dark Alley At The Levee
Exits: w -> The Dark Alley, e -> unexplored, s -> the levee (unexplored)
Notable: none yet.

## Main Street (general store/pet shop)
Exits: n -> General Store (unexplored), s -> Pet Shop (unexplored), e -> Main Street (weapon shop/Swordsmen), w -> Market Square
Notable: an oozing green gelatinous blob mob here.

## Main Street (weapon shop/Swordsmen)
Exits: n -> Weapon Shop (unexplored), s -> Entrance Hall To The Guild Of Swordsmen, e -> leaves town (unexplored), w -> Main Street (general store/pet shop)
Notable: **this is where the warrior/swordsman starting guild is** — south
exit leads to the Guild of Swordsmen. Beastly fidos present.
**BEST LEVEL-1 HUNTING ROOM (2026-07-19): no guard spawns here**, so fidos
can be killed without a guard assisting. Killed 2 fidos here safely, taking
zero damage. Fidos and gelatinous blobs both wander in and out; if the room
is empty, wait 1-2 minutes and `look` again.
**FATAL DANGER (2026-07-19, later session): the grudge-holding gelatinous
blob KILLED dummy here.** On entering, two blobs were present (no fidos). A
single `look` command elapsed one round and the grudge blob ("Hey! You're
the fiend that attacked me!!!") attacked unprompted, crushing 24 -> -5 in
~3 rounds; the character died before any flee was possible. LESSON: if ANY
gelatinous blob is in this room, DO NOT ENTER — leave and wait for a
blob-free, fido-present state, or hunt elsewhere. A blob's grudge persists
across sessions until it kills you. Death here left NO recoverable corpse
(this server does not drop a lootable PC corpse), so all gear was lost.

## Entrance Hall To The Guild Of Swordsmen
Exits: n -> Main Street (weapon shop/Swordsmen), e -> Bar Of Swordsmen
Notable: a knight guards the entrance; ATM here. This is the character's
home guild (confirmed by "Your guildmaster" in the practice yard beyond).

## Bar Of Swordsmen
Exits: w -> Entrance Hall To The Guild Of Swordsmen, s -> Tournament And Practice Yard
Notable: a bulletin board and a waiter NPC; furniture all smashed up.

## The Tournament And Practice Yard
Exits: n -> Bar Of Swordsmen, d -> a well leading down into darkness (unexplored)
Notable: **the guildmaster is here** — this is where `practice <skill>`
works for a Swordsman. Practiced and learned `kick` here on 2026-07-18
(now at "bad" proficiency).

## Main Street (west end, magic guild)
Exits: n -> Magic Shop (unexplored), s -> Guild Of Magic Users (unexplored — not our guild), e -> Main Street (bakery/armory), w -> Inside The West Gate Of Midgaard
Notable: a janitor, a cityguard, and beastly fidos present.

## Inside The West Gate Of Midgaard
Exits: e -> Main Street (west end, magic guild), s -> Wall Road, w -> closed gate (unexplored, leads outside city)
Notable: two Peacekeepers and four cityguards stationed here.

## Wall Road (north segment, by west gate)
Exits: n -> Inside The West Gate Of Midgaard, s -> Wall Road (with poor alley branch)
Notable: none yet.

## Wall Road (with poor alley branch)
Exits: n -> Wall Road (north segment), e -> Poor Alley (western end), s -> Wall Road (bridge segment)
Notable: some letters written on the wall.

## Wall Road (bridge segment)
Exits: n -> Wall Road (with poor alley branch), s -> bridge across the river (unexplored, leads outside city)
Notable: none yet.
