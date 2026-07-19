# Character: dummy

Update this after running `score`/`inventory`/`equipment` at the start and
end of every play session, so the next session picks up where this one left
off instead of re-discovering everything from scratch.

- **Level:** 1 ("Dummy the Swordpupil")
- **Class/race:** warrior-type, confirmed by guild membership — home guild is
  the **Guild of Swordsmen** (see Notes below). `skills`/`spells` commands
  aren't recognized by this MUD (`Huh!?!`) — use `practice` instead to see
  known/learnable skills.
- **HP / Mana / Moves:** 24/24 max HP, 100/100 Mana, 85 max Moves (checked
  2026-07-19 post-death via `score`)
- **Gold:** 0 gold coins, 87 exp (1913 exp needed to next level), 0 quest
  points. SETBACK 2026-07-19: DIED to the grudge-holding gelatinous blob in
  the weapon-shop Main Street room, losing all 20 gold, ~86 exp (173 -> 87),
  and all gear (no lootable corpse dropped on this server). RE-GEARED for
  free: the Donation Room "kind soul" gives a full starter set to any naked
  player who waits in the room ~1-3 min ("get some clothes on! Here, I will
  help." then equips you) — this is a reliable death-recovery source, NOT
  one-time. AC restored 100/10 -> 39/10.
- **Hunger/thirst:** BOTH RESOLVED 2026-07-19. Thirst: `drink fountain` at
  The Temple Square, free and repeatable. **Hunger: SOLVED — beastly fido
  corpses reliably contain "a piece of meat" plus ~10 gold.** `eat meat`
  cleared hunger completely ("You are hungry" no longer appears in `score`).
  Food is now a free, renewable byproduct of hunting fidos — no need to buy
  bakery food at all.
- **Location at last logout:** The Midgaard Donation Room, 2026-07-19 (logged
  out here right after being re-geared by the kind soul; full HP, full gear)

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
1x a piece of meat (confirmed via `inventory`, 2026-07-19) — emergency food
reserve, looted from a fido corpse. `eat meat` when `score` says hungry.

## Known spells/skills
Checked via `practice` (the `skills`/`spells` commands don't exist on this
MUD and return "Huh!?!"). `kick` is now **learned** (proficiency: "bad" —
improves with use), practiced 2026-07-18 in the Guild of Swordsmen's
Tournament And Practice Yard. 1 practice session remaining. No spells shown
(consistent with a warrior-type class, no mana-based abilities practiced).

## Current goal / quest
**Goal: grind exp/gold toward level 2 (need 1827 more exp).** Survival
problems (gear, water, food) are all solved — the open task is purely
levelling. The proven method is killing beastly fidos in guard-free rooms.

### Fido farming playbook (proven 2026-07-19 — use this)
1. Go to **Main Street (weapon shop / Guild of Swordsmen)** — the one
   guard-free room with fido traffic. Route from Temple Square: `s` `e` `e`.
2. `kill fido`. Fidos are an ideal level-1 target: across 3 fights they
   landed **zero** hits (AC 39 fully blocks them), each dies in ~4-6 rounds.
3. Each fido yields **~33 exp + 10 gold + 1 piece of meat**.
4. `get all from corpse` after every kill — this is the food + gold source.
5. If the room is empty, wait 1-2 min and `look`; mobs wander in.
6. At ~55 fidos per level this is slow but completely safe. Consider
   exploring for better exp once a few levels are gained.

### Hard-won safety rules (learned the hard way this session)
- **Never fight in a room with a cityguard / Peacekeeper / knight.** Guards
  ASSIST the mob you attack and hit for ~9 (a third of the HP bar). This
  nearly killed the character in Common Square.
- **Do not fight the oozing green gelatinous blob.** Terrible matchup: its
  AC is too good to hit reliably and it crushes for ~9. Worse, **it holds a
  grudge** — after fleeing one, it later found the character and attacked on
  sight ("Hey! You're the fiend that attacked me!!!"), taking 24 HP -> 7 in
  two rounds. Leave any room it is in.
- **HP regen is very slow: ~5 minutes per tick even asleep.** There is no
  cheap healing at level 1, so a bad fight costs a long recovery. `sleep`
  (not just `rest`) in a safe room; the Guild of Swordsmen entrance hall and
  Temple Square both work. Full 7->24 HP heal took roughly 5-8 minutes.
- Flee threshold: with only 24 max HP and 9-damage attackers in the world,
  `flee` at 15 HP, not lower. `flee` worked reliably every time.

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

2026-07-19 session (COMBAT SESSION — first real progress in the character's
history). Went hunting now that gear was sorted. Results: **4 fidos killed,
172 exp gained (1 -> 173), 20 gold earned (0 -> 20), hunger permanently
solved.** The breakthrough was looting fido corpses: each contains ~10 gold
AND a piece of meat, so the food problem that consumed two prior sessions
turned out to be a byproduct of ordinary hunting — the bakery is unnecessary.
Killed the first 2 fidos in the guard-free Main Street (weapon shop) room
taking zero damage. Then made a mistake attacking a fido in Common Square
where a cityguard assisted it (24 -> 15 HP); fled successfully, still got the
kill. Then attacked a gelatinous blob — couldn't land hits, took 9-damage
crushes, fled at 15. Later the same blob tracked the character down and
attacked on sight, dropping 24 -> 7 HP in two rounds; fled again and retreated
to the Temple. Slept back to full 24/24 HP and logged out safely at full
health. No deaths, no equipment lost. See the safety rules under "Current
goal" — the guard-assist and blob-grudge behaviours are the two things most
likely to kill this character.

## Notes
Hunger and thirst are both SOLVED as of 2026-07-19 and should not consume
future sessions: `drink fountain` at Temple Square for water, `eat meat`
from fido corpses for food. The Bakery is therefore optional — 20 gold is
banked and better saved for equipment upgrades than spent on food.
The Bakery has a baker NPC and a sign with shop instructions
(`buy`, `list`). Confirmed via `list` in-game:

| # | Item           | Cost |
|---|----------------|------|
| 1 | A danish pastry | 7   |
| 2 | A bread         | 14  |
| 3 | A waybread      | 70  |
All items shown as "Unlimited" availability.
