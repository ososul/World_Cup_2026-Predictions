Behavioral guidelines to reduce common LLM coding mistakes.
**Tradeoff:** bias toward caution over speed. For trivial tasks, use judgment.

**Project direction (scope).** The WC-2026 ratings + match-odds app (in `web/`) is the
**foundation of a larger, still-undefined platform** — not the finished scope. Build new
capabilities **incrementally on the existing seams** (`web/lib/data.ts` data seam, the pure
Python compute core, room reserved for a future `api/`); don't re-architect, and don't assume
the project is limited to what exists today. "Simplicity First" (§2) means *no speculative
gold-plating per task* — it does **not** mean the project stays small. Clarify new scope with
the user as it emerges.

- **Respect the stated phase.** If the task is "document/prepare," don't start building.

## 1. Think Before Coding
Don't assume, don't hide confusion, surface tradeoffs.
- State assumptions explicitly; if uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so.
- If something is unclear, stop and name it.

## 2. Simplicity First
Minimum code that solves the problem. Nothing speculative.
- No features, abstractions, or configurability beyond what was asked.
- No error handling for *impossible* scenarios. (Messy data — name mismatches,
  unmapped tournament strings, missing scores — is an EXPECTED scenario here, so
  validating those is in scope, not a violation of this rule.)
- If 200 lines could be 50, rewrite it.

## 3. Surgical Changes
Touch only what you must; clean up only your own mess.
- Don't "improve" adjacent code, comments, or formatting; match existing style.
- Don't refactor what isn't broken. Flag unrelated dead code — don't delete it.
- Remove only the imports/vars your own changes orphaned.
- Every changed line should trace to the request.

## 4. Goal-Driven Execution (numeric/statistical)
Define success criteria, loop until verified.
- **Deterministic code** (Elo update, win expectancy): assert against known reference
  values, e.g. dr=0 → 0.500, dr=100 → 0.640, dr=120 → 0.666, dr=800 → 0.990.
- **Model fitting**: "verify" means a proper score (log loss / RPS) improves on a
  **temporal** held-out split — never a random split, and never a binary pass/fail.
- **Data steps**: verify join coverage and mapping completeness (e.g. every tournament
  string resolves to a K-tier; every WC team name matches a rating).
- State a brief plan for multi-step tasks: `step → verify: check`.

**Working if:** fewer unnecessary diff changes, fewer overcomplication rewrites, and
clarifying questions come before implementation.