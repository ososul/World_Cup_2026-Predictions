"""EXPLORATION (not the production layer): run three 1X2 ideas on one match.

Reuses the Preliminary Elo engine to (1) replay history capturing each match's
PRE-MATCH rating difference dr (with the engine's H=100 home convention) and the
result, then (2) fit by maximum likelihood three ways of turning Elo's 2-outcome
win expectancy into P(home)/P(draw)/P(away):
    - Davidson  : Elo-consistent draw extension, scale fixed to Elo's 400, 1 param (nu)
    - OrderedLogit : latent dr*b with a +/-theta draw band, 2 params (b, theta)
    - Poisson   : independent goals, log-lambda linear in dr, 2 params (mu, beta)
Then it prints all three for a target match. This is a QUICK GLOBAL fit, not the
temporal-holdout validation that AGENTS.md requires before shipping a model.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prelim_elo"))

from prepare import load_and_prepare          # noqa: E402
from rating import match_deltas, win_expectancy, HOME_ADVANTAGE  # noqa: E402

INITIAL = 1500
EPS = 1e-12

# Target match (read straight off current_ratings.csv); neutral venue -> H = 0.
MATCH = ("France", "Iraq", 2134, 1708, True)  # home, away, R_home, R_away, neutral


# ---------------------------------------------------------------- replay
def replay():
    """Replay all played matches; return (final_ratings, records, fixtures).

    records: numpy arrays date, dr (incl. H), home_score, away_score, outcome
             outcome code: 0 home win, 1 draw, 2 away win.
    """
    played, fixtures = load_and_prepare()
    ratings: dict[str, int] = {}
    dates, drs, hss, ass, ocs = [], [], [], [], []
    for m in played:
        rh = ratings.get(m.home, INITIAL)
        ra = ratings.get(m.away, INITIAL)
        h = 0 if m.neutral else HOME_ADVANTAGE
        dates.append(m.date)
        drs.append(rh - ra + h)
        hss.append(m.home_score)
        ass.append(m.away_score)
        ocs.append(0 if m.home_score > m.away_score else 1 if m.home_score == m.away_score else 2)
        dh, da = match_deltas(rh, ra, m.neutral, m.k_eff, m.home_score, m.away_score)
        ratings[m.home] = rh + dh
        ratings[m.away] = ra + da
    rec = dict(
        date=np.array(dates),
        dr=np.array(drs, dtype=float),
        hs=np.array(hss, dtype=float),
        as_=np.array(ass, dtype=float),
        oc=np.array(ocs, dtype=int),
    )
    return ratings, rec, fixtures


# ---------------------------------------------------------------- models
def davidson_probs(dr, nu):
    """Davidson draw extension on Elo's own scale (gamma = 10**(dr/400))."""
    g = 10.0 ** (dr / 400.0)
    sg = 10.0 ** (dr / 800.0)
    den = g + 1.0 + nu * sg
    return g / den, nu * sg / den, 1.0 / den  # pH, pD, pA


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def ordlogit_probs(dr, b, theta):
    """Ordered-logistic: latent m = b*dr, symmetric draw band +/- theta."""
    m = b * dr
    pH = _sigmoid(m - theta)
    pA = _sigmoid(-m - theta)
    return pH, 1.0 - pH - pA, pA


def poisson_lams(dr, mu, beta):
    x = dr / 400.0
    return np.exp(mu + beta * x), np.exp(mu - beta * x)  # lam_home, lam_away


def poisson_probs(dr, mu, beta, ngrid=15):
    """1X2 from independent Poisson goals (vectorised over scalar or array dr)."""
    lam_h, lam_a = poisson_lams(np.atleast_1d(np.asarray(dr, float)), mu, beta)
    k = np.arange(ngrid + 1)
    logfac = np.cumsum(np.log(np.maximum(k, 1)))  # log k!  (log0!=0)
    # pmf[i, k] for each match i
    def pmf(lam):
        ll = -lam[:, None] + k[None, :] * np.log(lam[:, None]) - logfac[None, :]
        return np.exp(ll)
    ph, pa = pmf(lam_h), pmf(lam_a)
    upper = np.triu(np.ones((ngrid + 1, ngrid + 1)), 1)  # strictly-upper mask
    joint = ph[:, :, None] * pa[:, None, :]  # joint[i, hg, ag]
    pHv = (joint * upper.T).sum(axis=(1, 2))   # home goals > away goals
    pDv = np.einsum("ik,ik->i", ph, pa)        # equal
    pAv = (joint * upper).sum(axis=(1, 2))      # away goals > home goals
    return pHv, pDv, pAv


# ---------------------------------------------------------------- fitting
def nll_1x2(probs, oc):
    pH, pD, pA = probs
    p = np.choose(oc, [pH, pD, pA])
    return -np.mean(np.log(np.clip(p, EPS, 1.0)))


def golden(f, lo, hi, tol=1e-7, it=200):
    gr = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    c, d = b - gr * (b - a), a + gr * (b - a)
    fc, fd = f(c), f(d)
    for _ in range(it):
        if b - a < tol:
            break
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - gr * (b - a)
            fc = f(c)
        else:
            a, c, fc = c, d, fd
            d = a + gr * (b - a)
            fd = f(d)
    return 0.5 * (a + b)


def coord_min(f, bounds, sweeps=20):
    x = [0.5 * (lo + hi) for lo, hi in bounds]
    for _ in range(sweeps):
        for i, (lo, hi) in enumerate(bounds):
            def g(v, i=i):
                y = list(x)
                y[i] = v
                return f(y)
            x[i] = golden(g, lo, hi)
    return x


def fit_davidson(rec):
    nu = golden(lambda nu: nll_1x2(davidson_probs(rec["dr"], nu), rec["oc"]), 1e-4, 5.0)
    return (nu,)


def fit_ordlogit(rec):
    b, th = coord_min(
        lambda p: nll_1x2(ordlogit_probs(rec["dr"], p[0], p[1]), rec["oc"]),
        [(1e-4, 0.02), (1e-3, 2.0)],
    )
    return (b, th)


def poisson_negloglik(rec, mu, beta):
    lam_h, lam_a = poisson_lams(rec["dr"], mu, beta)
    ll = (rec["hs"] * np.log(lam_h) - lam_h + rec["as_"] * np.log(lam_a) - lam_a)
    return -np.mean(ll)  # drops constant log-factorial terms (irrelevant to argmax)


def fit_poisson(rec):
    mu, beta = coord_min(lambda p: poisson_negloglik(rec, p[0], p[1]),
                         [(-1.0, 2.0), (0.0, 1.5)])
    return (mu, beta)


# ---------------------------------------------------------------- metrics
def metrics(probs, oc):
    pH, pD, pA = (np.atleast_1d(x) for x in probs)
    ll = nll_1x2((pH, pD, pA), oc)
    cum1, cum2 = pH, pH + pD
    o1 = (oc == 0).astype(float)
    o2 = (oc <= 1).astype(float)
    rps = np.mean(0.5 * ((cum1 - o1) ** 2 + (cum2 - o2) ** 2))
    return ll, rps


def empirical_bin(rec, dr0, half=40):
    sel = np.abs(rec["dr"] - dr0) <= half
    oc = rec["oc"][sel]
    n = len(oc)
    if n == 0:
        return None
    return n, (oc == 0).mean(), (oc == 1).mean(), (oc == 2).mean()


# ---------------------------------------------------------------- run
def report(rec, label):
    home, away, rh, ra, neutral = MATCH
    dr = rh - ra + (0 if neutral else HOME_ADVANTAGE)
    we = win_expectancy(dr)

    dav = fit_davidson(rec)
    ol = fit_ordlogit(rec)
    po = fit_poisson(rec)

    print(f"\n================ FIT SAMPLE: {label}  (n={len(rec['oc']):,}) ================")
    base = np.bincount(rec["oc"], minlength=3) / len(rec["oc"])
    print(f"sample base rate     H/D/A = {base[0]:.3f} / {base[1]:.3f} / {base[2]:.3f}")
    bll, brps = metrics((np.full_like(rec['dr'], base[0]),
                         np.full_like(rec['dr'], base[1]),
                         np.full_like(rec['dr'], base[2])), rec["oc"])
    print(f"base-rate baseline   logloss={bll:.4f}  RPS={brps:.4f}")
    print(f"fitted params        Davidson nu={dav[0]:.3f} | "
          f"OrdLogit b={ol[0]:.5f} theta={ol[1]:.3f} | Poisson mu={po[0]:.3f} beta={po[1]:.3f}")

    print("\nin-sample fit quality (lower is better):")
    for name, pr in [("Davidson", davidson_probs(rec["dr"], *dav)),
                     ("OrderedLogit", ordlogit_probs(rec["dr"], *ol)),
                     ("Poisson", poisson_probs(rec["dr"], *po))]:
        ll, rps = metrics(pr, rec["oc"])
        print(f"  {name:<13} logloss={ll:.4f}  RPS={rps:.4f}")

    print(f"\n--- {home} ({rh}) vs {away} ({ra}),  neutral={neutral} -> dr={dr:+d},"
          f" We(home)={we:.4f} ---")
    print(f"{'model':<14}{'P(' + home + ' win)':>18}{'P(draw)':>12}{'P(' + away + ' win)':>16}{'check':>8}")
    rows = [("Davidson", davidson_probs(dr, *dav)),
            ("OrderedLogit", ordlogit_probs(dr, *ol)),
            ("Poisson", poisson_probs(dr, *po))]
    for name, pr in rows:
        pH, pD, pA = (float(np.ravel(x)[0]) for x in pr)
        print(f"{name:<14}{pH:>18.4f}{pD:>12.4f}{pA:>16.4f}{pH + pD + pA:>8.3f}")

    emp = empirical_bin(rec, dr)
    if emp:
        n, eh, ed, ea = emp
        print(f"{'empirical bin':<14}{eh:>18.4f}{ed:>12.4f}{ea:>16.4f}{'':>8}"
              f"   (dr in {dr - 40}..{dr + 40}, n={n})")

    if rows:
        lh, la = poisson_lams(np.array([dr], float), *po)
        print(f"\nPoisson expected goals: {home} {lh[0]:.2f}  -  {la[0]:.2f} {away}")


def main():
    ratings, rec, fixtures = replay()
    print(f"replayed {len(rec['oc']):,} matches; "
          f"Argentina={ratings.get('Argentina')} Austria={ratings.get('Austria')}")
    report(rec, "all history")

    since = rec["date"] >= "2002-01-01"
    rec2 = {k: (v[since] if k != "date" else v[since]) for k, v in rec.items()}
    report(rec2, "since 2002-01-01")


if __name__ == "__main__":
    main()
