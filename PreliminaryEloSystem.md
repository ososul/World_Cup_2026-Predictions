# World Football Elo Rating System — Implementation Spec
# Source: eloratings.net/about (official). Baseline implementation — reproduce exactly.

## Rating update (applied after every match, to BOTH teams)
R_new = R_old + round( K_eff * (W - We) )

- Points change is rounded to the nearest integer PER TEAM before updating.
- Use PRE-MATCH ratings for both teams when computing We (do not update one team
  then use its new rating for the other).

## W — match result (per team)
- Win  -> W = 1.0
- Draw -> W = 0.5
- Loss -> W = 0.0
- Penalty-shootout result counts as a DRAW (W = 0.5 for both teams).
- Extra-time win/loss counts as a normal win/loss.

## We — win expectancy (per team)
dr_home = R_home - R_away + H        # H = 100 if home team has home advantage
dr_away = -dr_home
We_home = 1 / (10 ** (-dr_home / 400) + 1)
We_away = 1 - We_home
- H = 100 for the team playing at home; H = 0 when the match is at a neutral venue
  (use the dataset's `neutral` flag; if neutral, neither team gets the +100).
# DEVIATION (2026-06-23): this implementation uses H = 90, not the eloratings 100 — tuned
# down for the 2026 World Cup (declining / multi-host-diluted home advantage). The live
# value is the HOME_ADVANTAGE constant in prelim_elo/rating.py.
- 400 is the logistic divisor.

## K_eff — effective weight = base tournament weight * goal-difference multiplier
K_eff = K_base * G

### K_base (by match importance / tournament tier)
- 60 : World Cup finals
- 50 : continental championship finals and major intercontinental tournaments
- 40 : World Cup and continental qualifiers and major tournaments
- 30 : all other tournaments
- 20 : friendly matches
# NOTE: the dataset's `tournament` string does NOT map cleanly to these tiers.
# A lookup/classification table from tournament name -> K_base is required.

### G (goal-difference multiplier), N = absolute goal difference of the match
- N <= 1 (includes draws) : G = 1.0
- N == 2                  : G = 1.5
- N == 3                  : G = 1.75
- N >= 4                  : G = 1.75 + (N - 3) / 8
# G is the same for both teams and depends only on the match margin, not direction.

## Initialisation & conventions
- New / unseen team starts at R = 1500.
- Ratings are PROVISIONAL until a team has played ~30 matches (flag only;
  the same K is used — do NOT use a higher K for provisional teams in the baseline).
- Before rounding, the system is zero-sum: P_home + P_away = 0
  (because W_home + W_away = 1 and We_home + We_away = 1). Per-team rounding can
  introduce a +/-1 point discrepancy; this matches the official behaviour.

## Worked sanity check (must reproduce)
- dr = 0   -> We = 0.500
- dr = 100 -> We = 0.640
- dr = 120 -> We = 0.666
- dr = 800 -> We = 0.990