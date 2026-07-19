# World State (tbaMUD @ localhost:4000)

## Map: Midgaard (city center)

- **Temple Square** (down/d from Temple of Midgaard): fountain, janitor. Exits: n(temple) e(Grunting Boar Inn) s(Market Square) w(Clerics' Guild)
- **Market Square** (center of Midgaard, cityguards here): statue. Exits: n(Temple Square) s(Common Square) e(Main Street→general store/pet shop) w(Main Street→bakery/armory)
- **Common Square** (s of Market Square): beastly fidos scavenging garbage. Exits: n(Market Square) e(dark alley) w(poor alley) s(nasty smell)
- **Main Street, east of Market Square**: general store (n), Pet Shop (s). Continues e toward weapon shop/Guild of Swordsmen/town exit.
- **Main Street, west of Market Square — Bakery corner**: Armory (s), **Bakery (n)**. Exits: n e s w
- **Main Street, further west**: magic shop (n), Guild of Magic Users (s), continues w to West Gate.
- **Inside the West Gate**: towers/footbridge, cityguards + Peacekeeper. Wall Road leads s. Gate (w) is closed.

## Shops

### The Bakery
- Location: one square north of the Main Street/Bakery-Armory corner (west side of Market Square).
- Description: small bakery, smells of danish and fine bread; shelves of bread/danish; small sign on counter; NPC "the baker" present.
- Exits: s (back to Main Street)
- Menu (via `list`):
  | # | Item | Cost |
  |---|------|------|
  | 1 | A danish pastry | 7 |
  | 2 | A bread | 14 |
  | 3 | A waybread | 70 |
- Sign instructions: `buy` purchases bread/pastry; `list` shows price & stock.
