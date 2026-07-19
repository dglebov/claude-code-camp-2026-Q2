# MUD character check-in — dummy

Connected to the tbaMUD server on localhost:4000, logged in as `dummy`, and
checked in on stats and inventory. Logged out cleanly afterward.

## Stats (`score`)
- 24/24 HP, 100/100 Mana, 84/85 Moves (moves had regenerated a bit since the
  last logout, which showed 79/85)
- Level 1, "Dummy the Swordpupil"
- 1 exp, needs 1999 exp for level 2
- 0 gold coins, 0 quest points, 0 quests completed
- Hungry and thirsty
- Standing in The Bakery — same room as at last logout

## Inventory (`inventory`)
Nothing carried — still completely empty.

## Equipment (`equipment`)
Nothing equipped — still completely bare.

## Skills/spells (`practice`)
`skills` and `spells` aren't valid commands on this server (both returned
"Huh!?!"). Used `practice` instead: the character has 2 unspent practice
sessions and knows of one skill, `kick`, which is not yet learned. No spells
are listed, consistent with a warrior-leaning class.

## Bottom line
Nothing has changed since the character was created — no gold earned, no
exp gained, no gear picked up, still parked in The Bakery. The character is
essentially in the exact same state as the last session left it. The one
new piece of information this check-in surfaced is the `practice` skill
list (kick, unlearned, 2 sessions available) and the correct command to use
for that (`practice`, not `skills`/`spells`).

## Notes updated
`data/character.md` was refreshed with the current stats, confirmed empty
inventory/equipment, the practice/skills finding, and a note about the
`skills`/`spells` commands not existing on this server. `data/map.md` was
left as-is since no new rooms were explored this session (character stayed
in The Bakery throughout).

## Session log
Full raw transcript of this session saved alongside this file as
`session_log.txt`.
