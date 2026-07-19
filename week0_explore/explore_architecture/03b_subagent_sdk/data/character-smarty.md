# Character: smarty

Update this after running `score`/`inventory`/`equipment` at the start and
end of every play session, so the next session picks up where this one left
off instead of re-discovering everything from scratch.

- **Level:** 1 ("Smarty the Apprentice of Magic")
- **Class/race:** mage-type, confirmed by guild membership — home guild is
  the **Guild Of Magic Users** (a.k.a. "The Mages' Guild" / "Entrance To The
  Mages' Guild" in room titles; see Notes below). `skills`/`spells` commands
  aren't recognized by this MUD (likely `Huh!?!`, consistent with the dummy
  session) — use `practice` instead to see known/learnable spells.
- **HP / Mana / Moves:** 14 max HP, 100 max Mana, 83 max Moves. Max HP is
  brutally low — a single town mob fight can kill this character (see death
  note below). Rested back to full 14/14 HP before logging out, 2026-07-19.
- **Gold:** 0 gold coins, **32 exp** (2468 exp needed to next level), 0
  quest points. Gained +31 net exp this session by killing a beastly fido
  (33 exp), minus a ~2 exp death penalty.
- **Location at last logout:** The Midgaard Donation Room / Temple Of
  Midgaard area (respawned at the Temple after dying — see below),
  2026-07-19.

## Equipment
Nothing equipped. Confirmed via `equipment` ("You are using: Nothing.") —
unlike the "dummy" character, smarty has NOT yet visited the Midgaard
Donation Room (east off the Temple Of Midgaard) for starter gear. Worth
doing early next session, per the dummy character's experience.

## Inventory
Nothing carried. (confirmed via `inventory`, 2026-07-19, "You are carrying:
Nothing.")

## Known spells/skills
Checked via `practice` in The Mages' Laboratory (guildmaster's room).
Only one spell is offered at this level:
- `magic missile` — practiced twice this session, proficiency went
  not-learned -> **average** -> **superb**. 1 practice session remaining
  (started with 3, used 2).

## Current goal / quest
`magic missile` at superb proficiency and confirmed working in combat
(killed a fido with it, 33 exp). Still 0 gold, 32 exp (2468 to level 2),
no equipment. Next concrete steps:
1. **Get gold/gear WITHOUT fighting town mobs.** The Midgaard Donation Room
   does NOT work here (see WARNING below) — the "kind soul" only speaks
   flavor text and gives nothing. Need another source of starter gear.
2. **Do NOT fight anything in town** — town guards defend even trash mobs
   and will kill this level-1 character (see death note). To grind exp
   safely, look for solo mobs OUTSIDE the guarded city (e.g. beyond the
   west city gate) but only at higher HP/with an escape plan, or find a
   truly weak isolated mob. Consider gaining a level first via any safe
   means before risking combat again.
3. Save the 1 remaining practice session for higher-level spells.

## DEATH / DANGER LOG (read before fighting!)
- **2026-07-19: DIED** at level 1 on Main Street (west end, magic guild).
  Cast `magic missile` at a beastly fido — a **Peacekeeper "jumped to the
  aid of the beastly fido"** and multiple guards thrashed me. I killed the
  fido (+33 exp) but a Peacekeeper thrash for ~4 then a killing blow ended
  me at 14 max HP. Respawned at the Temple with 1 HP, lost ~2 exp.
- **LESSON: never attack ANY mob standing in a room with a Peacekeeper /
  cityguard.** In this MUD the guards assist the mob, not you, and one
  guard hit (~4-10 dmg) is lethal at 14 HP. The beastly fidos on Main
  Street are a TRAP for this reason — guards are always nearby.

## Notes
Fresh character as of 2026-07-19 — first session. The Entrance To The
Mages' Guild (one room north of the Mages' Bar/Laboratory area) is guarded
by a sorcerer, a Peacekeeper, a cityguard, and a janitor; also has an ATM.
This confirms it's the correct guild for a mage-type character (mirrors how
the Guild of Swordsmen was confirmed for "dummy" via its guildmaster).
