# Prediction Phase — Kickoff Brief

Self-contained handoff for a fresh chat to start the **prediction layer** of the World Cup
2026 project. The rating engine (**Preliminary Elo**) is complete and validated; this phase
turns ratings into match + tournament probabilities.

## 0. Read these first
- **`AGENTS.md` / `CLAUDE.md`** (identical) — working norms. Critical for this phase:
  model fitting is validated on a **temporal held-out split** with a **proper score
  (log loss / RPS)** — never a random split, never binary pass/fail. Work one step at a
  time and check in; don't run ahead. Re-verify live data before status recaps or acting.
- **`PreliminaryEloSystem.md`** — the exact Elo spec the ratings come from.

## 1. Goal
Build our own 2026 World Cup predictions from our self-built rating system (starting with
the Preliminary Elo, "prelim"): per-match outcome probabilities + full-tournament
simulation (advance / win probabilities). FIFA's own ranking is a **benchmark only** (§5).

## 2. What already exists — the rating engine
`prelim_elo/` — pure-Python stdlib, no deps, run from the project root:
- **`prepare.py`** — `load_and_prepare() -> (played, fixtures)`. Parses
  `data_set_copy/results.csv`, splits scored matches (`played`) from unplayed WC fixtures
  (`fixtures` = the **predict-set**), sorts chronologically (stable, file-order tiebreak),
  attaches `k_base`/`G`/`k_eff`. `Match` dataclass: date, home, away, neutral, tournament,
  k_base, home_score, away_score, g, k_eff.
- **`rating.py`** — pure math: `win_expectancy(dr)`, `result_w(hs, as)`,
  `match_deltas(r_home, r_away, neutral, k_eff, hs, as)`. `HOME_ADVANTAGE = 100`.
- **`engine.py`** — `run(record_history=False) -> (ratings, counts, last_date, n[, history])`.
  `INITIAL = 1500`, `PROVISIONAL_MATCHES = 30`. Replays all played matches in order.
- **`output.py`** — writes `current_ratings.csv`; `wc2026_teams(played, fixtures)` → 48-team set.
- **`export_web.py`** — writes `web/public/data/*.json`.

Outputs: `current_ratings.csv` (full ranked table); `web/` (Next.js app on **3100**,
manifest-driven). `tournament_tiers.json` = frozen tournament→K_base map.

Run / refresh:
```
python3 prelim_elo/output.py        # -> current_ratings.csv + prints WC-48 ranking
python3 prelim_elo/export_web.py    # -> web/public/data JSON
cd web && npm run dev               # -> http://localhost:3100
```

## 3. Live state (as of 2026-06-22 — changes as matches are entered)
- WC 2026: **40 played, 32 pending** (all group stage), latest played 2026-06-21.
- Predict-set = the pending `NA`-score WC rows in `results.csv`. **Knockout fixtures are not
  in the dataset** (they depend on group results) — the simulation must generate the bracket.
- New scores are entered by editing the `NA` rows in `data_set_copy/results.csv` as matches
  finish (line-exact replacement), then re-running the engine. Current top Elo: Argentina,
  Spain, France, England, Brazil… (re-run to refresh exact numbers).

## 4. The prediction task (what to build)
**(a) Match outcome model — rating difference → P(home) / P(draw) / P(away).**
Elo's `win_expectancy` is a 2-outcome win expectancy (draw = ½); football needs **1X2**, so a
draw has to be modelled somehow. **How to do this is an open design question — begin that chat
by discussing the modelling approach with the user; do NOT pre-select a method here.** Whatever
is chosen must use the **same home-advantage convention as the engine** (H=100 when
`neutral=FALSE`; WC hosts USA/Canada/Mexico get it, all other WC games are neutral).

**(b) Tournament projection.** Roll the chosen match model forward over the remaining fixtures
to get group standings (official WC tiebreakers) → knockout bracket → P(advance), P(reach
round), P(win). The projection approach is likewise an open design question — work it out with
the user. Knockout ties need a shootout resolution (in Elo a shootout is a draw / no rating
change, but advancement needs a winner — decide the rule with the user).

**Validation (per AGENTS.md):** fit any free parameters (draw width, rating scale) on matches
**before** a temporal cutoff; evaluate **log loss / RPS** on held-out **later** matches; must
beat the FIFA-ranking rank-order baseline. No random splits.

## 5. Conventions the prediction work must respect
- **`fifa_rankings.md` is REFERENCE / benchmark ONLY** — never a feature, data source, or
  training target. Compare rank order only.
- Ratings already bake in home advantage (H=100), goal-difference weighting, and
  shootouts-as-draws — don't double-count these in the outcome model.
- Dissolved teams aren't merged (no succession); same-day order = file order; rounding =
  half-away-from-zero (no practical effect).
- "Prelim" labeling is deliberate: a future improved rating system will sit alongside, so keep
  the prediction layer able to run off **any** rating source (consume `current_ratings.csv` /
  the engine; don't hard-couple to internals). Suggested home for new code: `prelim_pred/`.

## 6. First decisions to discuss with the user (before any code)
- The match-outcome modelling approach (the 1X2 / draw question in §4a) — this is the
  conversation to open the chat with; bring options, don't arrive with a pick.
- The tournament-projection approach.
- Shootout / knockout tie resolution.
- The temporal-split cutoff for validation.
- Where prediction code / output should live.
