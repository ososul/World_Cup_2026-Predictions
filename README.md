# World_Cup_2026-Predictions

A self-built football rating + prediction system. The first deliverable is **World Cup 2026** —
our own Elo ratings and match/tournament probabilities, surfaced in a Next.js app (`web/`).

**Scope:** this is the **foundation of a larger, evolving platform**, not a one-off project.
What lies beyond the current ratings/odds views is **intentionally open** and built up
incrementally as it's defined. The architecture is deliberately layered — Python is the single
source of truth for data, the UI reads it through one seam (`web/lib/data.ts`), and room is
reserved for a future backend/API — so new capabilities slot onto existing seams rather than
forcing a rewrite. Don't treat what exists today as the finished scope.

## Layout
- `prelim_elo/` — the Preliminary Elo rating engine (pure Python).
- `prelim_pred/` — the prediction layer: outcome models + the exporters that write JSON.
- `web/` — the Next.js frontend (reads the JSON the Python pipeline writes to `web/public/data`).
- `data_set_copy/` — the match dataset.

See `AGENTS.md` for working norms (incl. "Project direction") and `PREDICTION_KICKOFF.md` for
the prediction phase.
