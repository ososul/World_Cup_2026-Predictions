"""Outcome models: rating difference dr -> (P(home), P(draw), P(away)).

Davidson (the confirmed baseline): the Elo-consistent draw extension, with the
scale PINNED to Elo's own 400 divisor, so its single free parameter nu (draw
propensity) is fit by maximum likelihood and nothing else moves. The draw mass
is proportional to the geometric mean of the two sides' strengths, so it peaks
when teams are equal and shrinks in mismatches.

Also exposes the win-expectancy / expected-score helpers used to report how far
Davidson's implied expected score drifts from Elo's We (a confirmed reporting
requirement: the two coincide only at dr = 0).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prelim_elo"))

from rating import win_expectancy   # noqa: E402  (Elo's 2-outcome win expectancy)

from metrics import log_loss


def _probs_from_strength(g: float, sqrt_g: float, nu: float):
    """Davidson 1X2 from g = 10**(dr/400) and sqrt_g = 10**(dr/800)."""
    den = g + 1.0 + nu * sqrt_g
    return g / den, nu * sqrt_g / den, 1.0 / den


def davidson_probs(dr: float, nu: float):
    """1X2 probabilities for rating difference dr (Davidson, Elo's 400 scale)."""
    return _probs_from_strength(10.0 ** (dr / 400.0), 10.0 ** (dr / 800.0), nu)


def expected_score(probs) -> float:
    """Home expected points share implied by 1X2 probs (win=1, draw=0.5)."""
    p_home, p_draw, _ = probs
    return p_home + 0.5 * p_draw


def we_drift(dr: float, nu: float) -> float:
    """Davidson's implied expected score minus Elo's We at this dr (signed)."""
    return expected_score(davidson_probs(dr, nu)) - win_expectancy(dr)


def fit_davidson(samples) -> float:
    """Fit nu by minimising mean log loss on `samples` (1-D golden-section search).

    g and sqrt_g depend only on dr, not nu, so they are precomputed once and the
    search re-evaluates only the cheap arithmetic per candidate nu.
    """
    g = [10.0 ** (s.dr / 400.0) for s in samples]
    sqrt_g = [10.0 ** (s.dr / 800.0) for s in samples]
    outcomes = [s.outcome for s in samples]

    def objective(nu: float) -> float:
        probs = (_probs_from_strength(gi, sgi, nu) for gi, sgi in zip(g, sqrt_g))
        return log_loss(probs, outcomes)

    return _golden(objective, 1e-4, 5.0)


def _golden(f, lo: float, hi: float, tol: float = 1e-7, max_iter: int = 200) -> float:
    """Minimise a unimodal f on [lo, hi] by golden-section search."""
    r = (5 ** 0.5 - 1) / 2  # 0.618...
    a, b = lo, hi
    c, d = b - r * (b - a), a + r * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(max_iter):
        if b - a < tol:
            break
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - r * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + r * (b - a)
            fd = f(d)
    return 0.5 * (a + b)
