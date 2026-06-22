# Tournament → K-factor mapping (DRAFT for review)

Status: **draft — eyeball before we freeze it into the engine's lookup table.**
Covers all **200** distinct `tournament` strings in `data_set_copy/results.csv` (49,476 matches).
Numbers in parentheses = match count in the dataset.

## Tier → K scale (agreed)

| K | Meaning |
|----|---------|
| 60 | World Cup finals |
| 50 | Strongest continental finals + intercontinental majors |
| 45 | Other major continental finals |
| 40 | Major-confederation qualifiers + OFC final |
| 30 | Secondary / regional competitive championships, Nations Leagues |
| 20 | Friendlies, invitational tournaments, multi-sport games, non-FIFA |

Per-tier totals: 60 → 1 comp / 1,036 matches · 50 → 4 / 1,400 · 45 → 4 / 1,855 · 40 → 8 / 15,137 · 30 → 44 / 7,097 · 20 → 139 / 22,951.

Rule for qualifiers: the **big-six** confederation championship qualifiers sit at 40; qualifiers for everything below that inherit their parent tournament's (lower) tier.

---

## K = 60 — World Cup finals
- FIFA World Cup (1036)

## K = 50 — top continental finals + intercontinental majors
- Copa América (869)
- UEFA Euro (388)
- Confederations Cup (140)
- CONMEBOL–UEFA Cup of Champions (3)  *(Finalissima)*

## K = 45 — major continental finals
- African Cup of Nations (845)
- AFC Asian Cup (421)
- Gold Cup (420)
- CONCACAF Championship (169)  *(old Gold Cup)*

## K = 40 — major-confederation qualifiers + OFC final
- FIFA World Cup qualification (8771)
- UEFA Euro qualification (2824)
- African Cup of Nations qualification (2327)
- AFC Asian Cup qualification (829)
- CONCACAF Championship qualification (151)
- Gold Cup qualification (88)
- Copa América qualification (8)
- Oceania Nations Cup (139)  *(OFC final — weakest confederation, so 40 not 45)*

## K = 30 — secondary / regional competitive championships + Nations Leagues
- UEFA Nations League (658)
- CONCACAF Nations League (422)
- CONCACAF Nations League qualification (68)
- CECAFA Cup (620)
- Gulf Cup (410)
- COSAFA Cup (354) · COSAFA Cup qualification (27)
- AFF Championship (291) · AFF Championship qualification (62)
- Nordic Championship (283)
- British Home Championship (523)
- CFU Caribbean Cup (251) · CFU Caribbean Cup qualification (606)
- Amílcar Cabral Cup (235)
- Arab Cup (175) · Arab Cup qualification (31)
- UNCAF Cup (164)
- SAFF Cup (162)
- EAFF Championship (130) · EAFF Championship qualification (5)
- Central European International Cup (126)   ⚑ see flags
- CCCF Championship (123)
- WAFF Championship (114)
- Baltic Cup (106)
- AFC Challenge Cup (87) · AFC Challenge Cup qualification (92)
- Balkan Cup (87)
- Olympic Games (78)   ⚑ see flags
- Asian Games (368)   ⚑ see flags
- All-African Games (70)   ⚑ see flags
- UDEAC Cup (70)
- UNIFFAC Cup (15)
- West African Cup (54)
- Pan American Championship (39)   ⚑ see flags
- Oceania Nations Cup qualification (31)
- Dynasty Cup (29)  *(East Asian championship, EAFF predecessor)*
- ASEAN Championship (26) · ASEAN Championship qualification (2)
- AFC Solidarity Cup (13)
- CAFA Nations Cup (10)
- NAFC Championship (6)
- NAFU Championship (4)
- Nations Cup (6)   ⚑ see flags (generic name)
- Melanesia Cup (64)

## K = 20 — friendlies, invitationals, multi-sport games, non-FIFA
Default bucket — everything not listed above. Grouped for review:

**Friendly + organised friendly windows**
- Friendly (18387), FIFA Series (57), CONCACAF Series (35)

**Invitational tournaments** (host-run, no title at stake)
- Merdeka Tournament (599), King's Cup (253), Korea Cup (155), Nehru Cup (89), Kirin Cup (79),
  Indonesia Tournament (75), Cyprus International Tournament (70), Vietnam Independence Cup (60),
  African Friendship Games (55), Malta International Tournament (53), Coupe de l'Outre-Mer (42),
  Brazil Independence Cup (37), USA Cup (37), United Arab Emirates Friendship Tournament (31),
  Lunar New Year Cup (25), Merlion Cup (25), MSG Prime Minister's Cup (23), Prime Minister's Cup (22),
  Kirin Challenge Cup (22), ABCS Tournament (20), Jordan International Tournament (17),
  Simba Tournament (17), Intercontinental Cup (17), Kuneitra Cup (15), Millennium Cup (15),
  Dunhill Cup (15), Nile Basin Tournament (14), King Hassan II Tournament (12), Unity Cup (12),
  Miami Cup (12), Philippine Peace Cup (12), Palestine International Championship (11),
  Tournament Burkina Faso (11), SKN Football Festival (11), Atlantic Cup (11), Rous Cup (11),
  Tournoi de France (10), Beijing International Friendship Tournament (10), VFF Cup (9), Dragon Cup (9),
  Four Nations Tournament (8), Marlboro Cup (8), Mundialito (7), Mahinda Rajapaksa Cup (7),
  Tri Nation Tournament (7), Mapinduzi Cup (7), International Tournament of Peoples, Cultures and Tribes (7),
  Morocco, Capital of African Football (6), Peace Cup (6), Mauritius Four Nations Cup (5), OSN Cup (4),
  Diamond Jubilee International Football Tournament (4), Matthews Cup (4), Al Ain International Cup (4),
  Joe Robbie Cup (4), Scania 100 Tournament (4), Guangzhou International Friendship Tournament (4),
  Dakar Tournament (4), Navruz Cup (4), Great Wall Cup (4), Canadian Shield (4), Three Nations Cup (3),
  Outrigger Challenge Cup (3), Zambian Independence Tournament (3), Phillip Seaga Cup (3),
  Hungary Heritage Cup (3), Tri-Nations Series (3), Cup of Ancient Civilizations (2), Four Nations' Cup (2),
  Atlantic Heritage Cup (2), Mukuru 4 Nations (2), Tri-Nations Cup (2), Évence Coppée Trophy (1),
  Open International Championship (1), Real Madrid 75th Anniversary Cup (1), FIFA 75th Anniversary Cup (1),
  Copa Confraternidad (1), South Asian Super Cup (1), Palestine Cup (58)

**Bilateral trophy series** (recurring two-nation cups)
- Copa Chevallier Boutell (29), Copa Lipton (28), Copa Newton (26), Copa Roca (23),
  Copa Paz del Chaco (23), Soccer Ashes (21), Copa del Pacífico (19), Copa Rio Branco (18),
  Copa Juan Pinto Durán (16), Copa Carlos Dittborn (16), Copa Oswaldo Cruz (16),
  Copa Premio Honor Uruguayo (15), Copa Artigas (13), Trans-Tasman Cup (12),
  Copa Premio Honor Argentino (12), Copa Bernardo O'Higgins (10), Superclásico de las Américas (8),
  Copa Ramón Castilla (6), Copa Félix Bogado (6)

**Multi-sport games** (football as one event; below confederation flagship)
- South Pacific Games (205), Southeast Asian Games (182), Indian Ocean Island Games (110),
  Pacific Games (75), Southeast Asian Peninsular Games (68), South Asian Games (68),
  Central American and Caribbean Games (63), South Pacific Mini Games (39),
  Far Eastern Championship Games (30), Inter Games (19), East Asian Games (17),
  Pacific Mini Games (15), GaNEFo (14), Inter-Allied Games (13), Bolivarian Games (12),
  Afro-Asian Games (4)

**Non-FIFA / unrecognised-territory football**
- Island Games (394), Muratti Vase (220), CONIFA World Football Cup (101),
  Windward Islands Tournament (101), Viva World Cup (60), CONIFA European Football Cup (49),
  ELF Cup (16), FIFI Wild Cup (10), CONIFA Asia Cup (8), Tynwald Hill Tournament (6),
  CONIFA World Football Cup qualification (5), Corsica Cup (4), CONIFA Africa Football Cup (4),
  Niamh Challenge Cup (3), CONIFA South America Football Cup (3), World Unity Cup (3),
  Cup of Ancient Civilizations (2), Marianas Cup (2), TIFOCO Tournament (1), The Other Final (1),
  ConIFA Challenger Cup (1), CONIFA World Cup qualification (1), Benedikt Fontana Cup (1)

---

## ⚑ Flagged for your call (genuinely debatable — currently at 30)

1. **Olympic Games (78)** — set to 30, but every match here is 1908–1928, when the Olympic
   tournament *was* football's de-facto world championship (pre-World-Cup). Arguable case for 40–50
   for that era. Tiny volume, near-zero effect on current ratings.
2. **Asian Games (368) & All-African Games (70)** — continental-scale multi-sport games, kept at 30
   while the smaller/island games sit at 20. Boundary call: drop to 20 for consistency, or keep at 30
   as genuine continental competition of their era.
3. **Central European International Cup (126)** — the prestigious 1927–1960 tournament among the
   Central European powers (Italy, Austria, Hungary, Czechoslovakia…). Currently 30; defensible at 40.
4. **Pan American Championship (39)** — the Americas' continental championship (1952–1960). Currently
   30; defensible at 40.
5. **Nations Cup (6)** — generic, ambiguous name; parked at 30. Could verify which competition this
   actually is, or drop to 20.

Non-flagged but worth a glance: the **multi-sport games** and **non-FIFA** groups are the largest
"could-go-either-way at 20" clusters — Island Games (394) and Muratti Vase (220) are sizeable, but
they involve non-FIFA micro-territories that never meet World Cup contenders, so 20 (or exclusion) is
low-stakes either way.
