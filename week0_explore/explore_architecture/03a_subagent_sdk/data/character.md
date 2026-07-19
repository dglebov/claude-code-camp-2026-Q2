# Character: dummy

Update this after running `score`/`inventory`/`equipment` at the start and
end of every play session, so the next session picks up where this one left
off instead of re-discovering everything from scratch.

- **Level:** 1 ("Dummy the Swordpupil")
- **Class/race:** warrior-type, confirmed by guild membership — home guild is
  the **Guild of Swordsmen** (see Notes below). `skills`/`spells` commands
  aren't recognized by this MUD (`Huh!?!`) — use `practice` instead to see
  known/learnable skills.
- **HP / Mana / Moves:** 24/24 HP, 100/100 Mana, 29/85 Moves (checked
  2026-07-19 via `score`, end of session; moves regenerate over time when idle)
- **Gold:** 0 gold coins, 1 exp (1999 exp needed to next level), 0 quest
  points — unchanged since last session, no progress made
- **Hunger/thirst:** THIRST RESOLVED 2026-07-19 — `drink fountain` at The
  Temple Square (the large blue-streaked marble fountain, enchanted/never
  runs dry) works and is free. `score` no longer shows "You are thirsty."
  Still **hungry** — no free food source found this session (see Notes).
- **Location at last logout:** The Temple Square (fountain room), after
  `quit` from here, 2026-07-19

## Equipment
Fully equipped as of 2026-07-18 — a "kind and caring soul" NPC in the Midgaard
Donation Room (east off the Temple of Midgaard) gave a full set of starter
gear unprompted. Armor class improved from 100/10 to 39/10 (lower is better
here). Confirmed via `equipment`:
candle (light), 2 leather rings, 2 leather gorgets, breast plate, leather
cap, bronze leggings, leather boots, leather gloves, leather sleeves, shield,
brown leather cape, old leather belt, 2 leather wristguards, small sword
(wielded), metal staff (held).

## Inventory
Nothing carried. (confirmed via `inventory`, 2026-07-18, after donation-room
gear was auto-equipped rather than carried)

## Known spells/skills
Checked via `practice` (the `skills`/`spells` commands don't exist on this
MUD and return "Huh!?!"). `kick` is now **learned** (proficiency: "bad" —
improves with use), practiced 2026-07-18 in the Guild of Swordsmen's
Tournament And Practice Yard. 1 practice session remaining. No spells shown
(consistent with a warrior-type class, no mana-based abilities practiced).

## Current goal / quest
Gear and first skill (`kick`) sorted. Thirst is now solved for free (temple
fountain) and doesn't need revisiting unless it recurs. Still 0 gold, 1 exp
(1999 needed to level 2), and still hungry — no free food found. Next
concrete step: find low-level mobs to fight for exp/gold now that armor and
a weapon are equipped — the practice yard's `d` (well leading down into
darkness) off the Guild of Swordsmen is unexplored and worth checking, or
fight the beastly fidos/gelatinous blobs seen wandering Main Street/Common
Square. Once any gold is earned, cheapest bakery item is a danish pastry
(7 coins).

2026-07-19 session (earlier): navigated the documented Temple Of Midgaard ->
Bakery path (`s`, `s`, `w`, `n`) with a `look` after each move — every room
description and exit set matched map.md exactly, no map corrections
needed. Bakery `list` menu unchanged (danish pastry 7, bread 14, waybread
70, all unlimited). Still 0 gold so nothing purchased.

2026-07-19 session (this one): went looking for free food/water since gold
is 0. `drink fountain` at The Temple Square worked and fully cleared thirst
("You don't feel thirsty any more.") — free, repeatable water source, no
gold needed. Searched for free food: the Midgaard Donation Room's "kind and
caring soul" NPC (source of the earlier free starter gear) had no food to
give this time — `ask soul about food` got no useful reply and `inventory`
after showed nothing new. Checked Common Square and The Dump (beastly fidos
"mucking through the garbage looking for food" there) but there's no
lootable/edible garbage object, just flavor text. Walked north out of the
Temple (By The Temple Altar -> Behind The Temple Altar -> The Great Field
Of Midgaard, into the countryside) looking for anything edible like fruit
trees/bushes — scenery only (grass, oak trees), no interactable food items,
and didn't push further into unmapped wilderness alone at level 1. Ended
the session still hungry; free food remains unfound. Likely next food
options: earn a little gold (fight weak mobs) for the 7-coin danish pastry,
or explore further/differently for a food source (e.g. the unexplored
General Store, Grunting Boar Inn bar/kitchen, or deeper countryside/sewer).

## Notes
Character is hungry (per `score`, still true as of 2026-07-19) — consider
buying food from the baker soon, once gold is available; thirst is no
longer an issue thanks to the free Temple Square fountain (`drink
fountain`). The Bakery has a baker NPC and a sign with shop instructions
(`buy`, `list`). Confirmed via `list` in-game:

| # | Item           | Cost |
|---|----------------|------|
| 1 | A danish pastry | 7   |
| 2 | A bread         | 14  |
| 3 | A waybread      | 70  |
All items shown as "Unlimited" availability.
