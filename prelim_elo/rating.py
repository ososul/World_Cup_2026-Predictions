"""Preliminary Elo System (spec: PreliminaryEloSystem.md) - Step 3: per-match update.

Implements the rating math from PreliminaryEloSystem.md: win expectancy, match
result W, and the per-team point change. Pre-match ratings in -> integer point
changes out; no state, no I/O.
"""
from __future__ import annotations

import math

HOME_ADVANTAGE = 100  # added to the home side's rating difference at a non-neutral venue


def win_expectancy(dr: float) -> float:
    """Elo win expectancy for rating difference dr (dr already includes home advantage)."""
    return 1.0 / (10 ** (-dr / 400) + 1)


def result_w(home_score: int, away_score: int) -> tuple[float, float]:
    """Per-team result W (home, away): win=1.0, draw=0.5, loss=0.0.

    Scores include extra time but not penalties, so a shootout already reads as a draw.
    """
    if home_score > away_score:
        return 1.0, 0.0
    if home_score < away_score:
        return 0.0, 1.0
    return 0.5, 0.5


def _round_half_away(x: float) -> int:
    """Round to nearest integer with halves going away from zero (2.5->3, -2.5->-3).

    The spec says "nearest integer" but does not fix the .5 tie-break; this is the
    conventional symmetric choice and avoids Python round()'s banker's rounding.
    """
    return math.floor(x + 0.5) if x >= 0 else math.ceil(x - 0.5)


def match_deltas(r_home: float, r_away: float, neutral: bool, k_eff: float,
                 home_score: int, away_score: int) -> tuple[int, int]:
    """Integer rating changes (home, away) for one match, using pre-match ratings.

    Both expectancies use the pre-match ratings; each side is rounded independently
    (per the spec this can leave a +/-1 zero-sum discrepancy, matching official behaviour).
    """
    h = 0 if neutral else HOME_ADVANTAGE
    dr_home = r_home - r_away + h
    we_home = win_expectancy(dr_home)
    we_away = 1.0 - we_home
    w_home, w_away = result_w(home_score, away_score)
    return (
        _round_half_away(k_eff * (w_home - we_home)),
        _round_half_away(k_eff * (w_away - we_away)),
    )


def _verify() -> None:
    print("=== Step 3: per-match Elo update ===")

    # Win expectancy against the spec's reference table.
    for dr, expected in {0: 0.500, 100: 0.640, 120: 0.666, 800: 0.990}.items():
        got = win_expectancy(dr)
        assert round(got, 3) == expected, f"We({dr})={got:.4f}, expected {expected}"
        print(f"  We(dr={dr:>3}) = {got:.4f} -> {round(got, 3):.3f}  (ref {expected:.3f})  OK")

    # Zero-sum before rounding (any k_eff, any dr).
    we_h = win_expectancy(100)
    pre = 60 * (1.0 - we_h) + 60 * (0.0 - (1.0 - we_h))
    assert abs(pre) < 1e-9
    print(f"  zero-sum pre-rounding: sum = {pre:.1e}  OK")

    # Worked full updates (hand-checkable).
    dh, da = match_deltas(1500, 1500, neutral=True, k_eff=20.0, home_score=1, away_score=0)
    assert (dh, da) == (10, -10), (dh, da)
    print(f"  equal teams, neutral, 1-0 home win, k_eff=20 -> (+{dh}, {da})  OK")

    dh, da = match_deltas(1500, 1500, neutral=False, k_eff=20.0, home_score=1, away_score=1)
    assert (dh, da) == (-3, 3), (dh, da)
    print(f"  equal teams, home advantage, 1-1 draw, k_eff=20 -> ({dh}, +{da})  OK")

    assert _round_half_away(2.5) == 3 and _round_half_away(-2.5) == -3
    print("  round-half-away tie-break: 2.5->3, -2.5->-3  OK")


if __name__ == "__main__":
    _verify()
