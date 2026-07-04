# WC-2026 Projection — Backlog (post-v1)

The 7-phase tournament-projection build is **complete** (all phases shipped 2026-07-04;
see the plan in `~/.claude/plans/i-want-your-help-glistening-wand.md`). This file holds the
work that was explicitly deferred out of v1 — kept here, in the repo, so it survives and can
be picked up later. Nothing here is scheduled; the user chooses what (if anything) comes next.

Guardrails that apply to all of it (from AGENTS.md): validate model fitting on a **temporal**
held-out split with log loss / RPS, never a random split; `fifa_rankings.md` is a benchmark
only, never a model input; ratings already include home advantage, GD weighting and
shootouts-as-draws — don't double-count; stay on the existing seams (pure-Python compute →
JSON → `web/lib/data.ts` → UI).

## 1. Pens ladder — HIGH priority add-on (design settled 2026-07-04)

Replaces the v1 `pens = 0.5` assumption with a fitted shootout model.

- **Rung 2:** `σ(c·dr)` — one parameter.
- **Rung 3:** `σ(c·dr + d·(hA − hB))` where `h` = log-odds of a beta-binomial-shrunk shootout
  win rate, `(wins + m/2)/(n + m)`, with histories built **WALK-FORWARD** (a 2010 fit row
  uses pre-2010 shootouts only — leakage guard). `m` tuned on a nested temporal split inside
  pre-2024 (or fixed ≈ 10).
- **Fit** pre-2024; **judge** against the 50/50 baseline on the 2024+ holdout (~50 shootouts —
  thin, be honest) by log loss; ship the winner.
- Ignore `first_shooter` (coin toss, unknowable pre-match). Report join coverage of
  shootouts → dr.
- **Sub-refinement for later:** recency decay on histories (squad turnover).

## 2. Elo update within the projection

Monte Carlo machinery so ratings move as the simulated tournament progresses; fattens the
champion tails.

## 3. Results-entry UI

A page that writes to `results.csv` / `shootouts.csv` instead of hand-editing them.

## 4. Better rating system

Separate project; swaps in via the seams + a param refit.

## 5. Joint events / conditional brackets

MC-only.

## 6. Full FIFA third-place allocation logic

Only needed for pre-tournament simulation.

## 7. Interactive what-if bracket explorer

Needs a TS port of the DP or an API.

## 8. Locked prediction snapshots — user-confirmed want (2026-07-04)

v1 shows as-of-now quotes everywhere — for played matches these are mildly hindsight-biased
(the ratings already include the result). Later: freeze the full projection (per-match probs +
reach) at user-chosen checkpoints (e.g. R32 field set, end of R32 / R16), stored as dated
snapshot files that never regenerate, shown alongside the live view — so locked forecasts can
be scored against actual tournament outcomes. The live stateless export stays the default.
