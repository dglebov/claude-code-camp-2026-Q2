Found it — and it turns out dummy never left. According to the notes from last session, the character logged out inside The Bakery, and `look` on login confirmed that's still exactly where we are:

> **The Bakery**
> You are standing inside the small bakery. A sweet scent of danish and fine bread fills the room. The bread and Danish are arranged in fine order on the shelves, and seem to be of the finest quality.
> A small sign is on the counter.
> [ Exits: s ]
> The baker looks at you calmly, wiping flour from his face with one hand.

A sign on the counter explains the shop commands (`buy` to purchase, `list` to see prices), so I ran `list` at the baker to pull up the menu:

| # | Item            | Cost (coins) | Available |
|---|-----------------|--------------|-----------|
| 1 | A danish pastry | 7            | Unlimited |
| 2 | A bread         | 14           | Unlimited |
| 3 | A waybread      | 70           | Unlimited |

One catch: dummy is currently broke (0 gold coins), so nothing on the menu is affordable yet — even the cheapest item (the danish pastry at 7 coins) is out of reach until some gold is earned. The character is also hungry and thirsty per `score`, so buying a danish or bread here is a good near-term goal once there's gold in hand.

I logged the character out cleanly (`quit` → `0` at the menu) before stopping the connection, so the character is left in a clean, logged-out state — still physically located in The Bakery for next time.
