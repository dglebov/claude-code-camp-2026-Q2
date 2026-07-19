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
- **HP / Mana / Moves:** 14/14 HP, 100/100 Mana, 83/83 Moves (checked
  2026-07-19 via `score`, unchanged across the session — no combat/travel
  cost incurred)
- **Gold:** 0 gold coins, 1 exp (2499 exp needed to next level), 0 quest
  points — fresh character, no progress made yet
- **Location at last logout:** The Mages' Laboratory (south end of the
  Guild Of Magic Users, off Main Street west end — guildmaster NPC is here),
  reached via `s`, `s`, `w`, `w`, `s`, `s`, `e` from The Temple Of Midgaard
  starting room, then `quit` from here, 2026-07-19

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
Spell sorted (`magic missile` at superb proficiency). Still 0 gold, 1 exp
(2499 needed to level 2), and no equipment at all. Next concrete steps:
1. Visit the Midgaard Donation Room (east off The Temple Of Midgaard) to
   pick up starter gear, the way "dummy" did.
2. Use the last practice session (1 remaining) once more spells become
   available at a higher level, or save it.
3. Find low-level mobs to fight for exp/gold — `magic missile` is now
   learned and should be usable in combat (`cast 'magic missile' <target>`).

## Notes
Fresh character as of 2026-07-19 — first session. The Entrance To The
Mages' Guild (one room north of the Mages' Bar/Laboratory area) is guarded
by a sorcerer, a Peacekeeper, a cityguard, and a janitor; also has an ATM.
This confirms it's the correct guild for a mage-type character (mirrors how
the Guild of Swordsmen was confirmed for "dummy" via its guildmaster).
