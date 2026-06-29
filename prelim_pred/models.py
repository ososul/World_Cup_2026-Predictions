"""Outcome models: rating difference dr -> (P(home), P(draw), P(away)).

Davidson (the confirmed baseline): the Elo-consistent draw extension, with the
scale PINNED to Elo's own 400 divisor, so its single free parameter nu (draw
propensity) is fit by maximum likelihood and nothing else moves. The draw mass
is proportional to the geometric mean of the two sides' strengths, so it peaks
when teams are equal and shrinks in mismatches.

Ordered logistic: an ordinal model with a latent strength gap m = b*dr and a symmetric
draw band +/- theta (a draw when the latent gap lands inside it). Two free parameters
(slope b, half-band theta); the scale is FREE (not pinned to 400) and fit alongside theta
by maximum likelihood.

Poisson (independent goals): log lambda_home = mu + beta*(dr/400), log lambda_away =
mu - beta*(dr/400); each team's goals are independent Poisson and the 1X2 falls out of the
score grid. Two free parameters (mu baseline, beta gap->goals), fit to the realised
SCORELINES (not the 1X2) by maximum likelihood. Kept as the validation baseline.

Dixon-Coles: plain Poisson plus a one-parameter (rho) dependence factor tau on the four
lowest score cells (0-0, 1-0, 0-1, 1-1), correcting independent Poisson's under-prediction of
low-scoring draws. rho = 0 recovers plain Poisson exactly (nested). Three free parameters
(mu, beta, rho), fit to the scorelines by maximum likelihood.

Also exposes the win-expectancy / expected-score helpers used to report how far
Davidson's implied expected score drifts from Elo's We (a confirmed reporting
requirement: the two coincide only at dr = 0).
"""
from __future__ import annotations

import math
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


def _sigmoid(z: float) -> float:
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)  # avoids overflow of exp(-z) when z is large and negative
    return e / (1.0 + e)


def ordlogit_probs(dr: float, b: float, theta: float):
    """1X2 probabilities for rating difference dr (ordered logistic).

    Latent strength gap m = b*dr; a draw when m falls inside the band [-theta, +theta].
    """
    m = b * dr
    p_home = _sigmoid(m - theta)
    p_away = _sigmoid(-m - theta)
    return p_home, 1.0 - p_home - p_away, p_away


def poisson_lambdas(dr: float, mu: float, beta: float) -> tuple[float, float]:
    """Expected goals (home, away) for rating difference dr (independent-Poisson model)."""
    x = dr / 400.0
    return math.exp(mu + beta * x), math.exp(mu - beta * x)


def _poisson_pmf(lam: float, max_goals: int) -> list[float]:
    """[P(0), .., P(max_goals)] of a Poisson(lam) via the P(k) = P(k-1)*lam/k recurrence."""
    pmf = [math.exp(-lam)]
    for k in range(1, max_goals + 1):
        pmf.append(pmf[-1] * lam / k)
    return pmf


def poisson_probs(dr: float, mu: float, beta: float, max_goals: int = 15):
    """1X2 from independent Poisson goals, renormalised over the truncated score grid."""
    lam_home, lam_away = poisson_lambdas(dr, mu, beta)
    ph = _poisson_pmf(lam_home, max_goals)
    pa = _poisson_pmf(lam_away, max_goals)
    p_home = p_draw = p_away = 0.0
    for i in range(max_goals + 1):
        phi = ph[i]
        for j in range(max_goals + 1):
            pij = phi * pa[j]
            if i > j:
                p_home += pij
            elif i == j:
                p_draw += pij
            else:
                p_away += pij
    total = p_home + p_draw + p_away
    return p_home / total, p_draw / total, p_away / total


def _dc_tau(x: int, y: int, lam_home: float, lam_away: float, rho: float) -> float:
    """Dixon-Coles dependence factor; 1.0 outside the four lowest score cells."""
    if x == 0 and y == 0:
        return 1.0 - lam_home * lam_away * rho
    if x == 1 and y == 0:
        return 1.0 + lam_away * rho
    if x == 0 and y == 1:
        return 1.0 + lam_home * rho
    if x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def dixoncoles_probs(dr: float, mu: float, beta: float, rho: float, max_goals: int = 15):
    """1X2 from Dixon-Coles goals (Poisson + low-score dependence), renormalised over the grid."""
    lam_home, lam_away = poisson_lambdas(dr, mu, beta)
    ph = _poisson_pmf(lam_home, max_goals)
    pa = _poisson_pmf(lam_away, max_goals)
    p_home = p_draw = p_away = 0.0
    for i in range(max_goals + 1):
        phi = ph[i]
        for j in range(max_goals + 1):
            pij = phi * pa[j]
            if i <= 1 and j <= 1:
                pij *= _dc_tau(i, j, lam_home, lam_away, rho)
                # with rho < 0, tau(1,0)/(0,1) dip below 0 only once a lambda exceeds 1/|rho|
                # (extreme dr, far outside [-800,800]); the clamp keeps the grid valid there
                if pij < 0.0:
                    pij = 0.0
            if i > j:
                p_home += pij
            elif i == j:
                p_draw += pij
            else:
                p_away += pij
    total = p_home + p_draw + p_away
    return p_home / total, p_draw / total, p_away / total


def score_logprob(dr: float, mu: float, beta: float, h: int, a: int,
                  rho: float = 0.0, max_goals: int = 15) -> float:
    """Log of the grid-normalised joint probability of the exact score (h, a).

    rho = 0.0 -> plain independent Poisson; rho != 0 -> Dixon-Coles. Used to compare how well
    each goals model fits actual scorelines (Dixon-Coles' primary advantage).
    """
    grid = max(max_goals, h, a)
    lam_home, lam_away = poisson_lambdas(dr, mu, beta)
    ph = _poisson_pmf(lam_home, grid)
    pa = _poisson_pmf(lam_away, grid)
    total = 0.0
    for i in range(grid + 1):
        for j in range(grid + 1):
            w = ph[i] * pa[j]
            if rho and i <= 1 and j <= 1:
                w *= _dc_tau(i, j, lam_home, lam_away, rho)
            if w > 0.0:
                total += w
    w_ha = ph[h] * pa[a]
    if rho and h <= 1 and a <= 1:
        w_ha *= _dc_tau(h, a, lam_home, lam_away, rho)
    return math.log(w_ha / total) if w_ha > 0.0 else float("-inf")


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


def fit_ordlogit(samples) -> tuple[float, float]:
    """Fit (b, theta) by minimising mean log loss on `samples` (coordinate descent).

    The objective inlines the ordered-logit log-prob of the realised outcome (avoiding
    per-match tuple building) since the fit re-evaluates it over every training match.
    """
    drs = [s.dr for s in samples]
    outcomes = [s.outcome for s in samples]
    n = len(samples)

    def objective(params) -> float:
        b, theta = params
        total = 0.0
        for dr, oc in zip(drs, outcomes):
            m = b * dr
            p_home = _sigmoid(m - theta)
            p_away = _sigmoid(-m - theta)
            p = p_home if oc == 0 else p_away if oc == 2 else 1.0 - p_home - p_away
            total -= math.log(p if p > 1e-15 else 1e-15)
        return total / n

    b, theta = _coord_descent(objective, [(1e-4, 2e-2), (1e-3, 2.0)])
    return b, theta


def fit_poisson(samples) -> tuple[float, float]:
    """Fit (mu, beta) to the realised scorelines by maximum likelihood (coordinate descent).

    Objective is the Poisson log-likelihood of both teams' goals, with the constant
    log-factorial terms dropped (they don't affect the argmax). Convex in (mu, beta).
    """
    drs = [s.dr for s in samples]
    home = [s.home_score for s in samples]
    away = [s.away_score for s in samples]
    n = len(samples)

    def objective(params) -> float:
        mu, beta = params
        total = 0.0
        for dr, h, a in zip(drs, home, away):
            x = dr / 400.0
            z_home = mu + beta * x
            z_away = mu - beta * x
            total -= h * z_home - math.exp(z_home) + a * z_away - math.exp(z_away)
        return total / n

    mu, beta = _coord_descent(objective, [(-1.0, 2.0), (0.0, 1.5)])
    return mu, beta


def fit_dixoncoles(samples) -> tuple[float, float, float]:
    """Fit (mu, beta, rho) to the scorelines by maximum likelihood (coordinate descent).

    Dixon-Coles log-likelihood = the independent-Poisson term plus log(tau) on the four lowest
    score cells. rho = 0 reduces to fit_poisson; the rho bound keeps tau positive on the data.
    """
    drs = [s.dr for s in samples]
    home = [s.home_score for s in samples]
    away = [s.away_score for s in samples]
    n = len(samples)

    def objective(params) -> float:
        mu, beta, rho = params
        total = 0.0
        for dr, h, a in zip(drs, home, away):
            x = dr / 400.0
            z_home = mu + beta * x
            z_away = mu - beta * x
            lam_home = math.exp(z_home)
            lam_away = math.exp(z_away)
            ll = h * z_home - lam_home + a * z_away - lam_away
            if h <= 1 and a <= 1:
                tau = _dc_tau(h, a, lam_home, lam_away, rho)
                ll += math.log(tau) if tau > 1e-12 else math.log(1e-12)
            total -= ll
        return total / n

    mu, beta, rho = _coord_descent(objective, [(-1.0, 2.0), (0.0, 1.5), (-0.2, 0.2)])
    return mu, beta, rho


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


def _coord_descent(f, bounds, sweeps: int = 6):
    """Minimise f over a small box by golden-section search on each coordinate in turn.

    f here (ordered-logit mean log loss) is smooth and convex, so a few sweeps converge.
    """
    x = [0.5 * (lo + hi) for lo, hi in bounds]
    for _ in range(sweeps):
        for i, (lo, hi) in enumerate(bounds):
            def g(v, i=i):
                y = list(x)
                y[i] = v
                return f(y)
            x[i] = _golden(g, lo, hi, tol=(hi - lo) * 1e-5)
    return x
