"""Check-in 4: add Dixon-Coles; validate it against plain Poisson (the promotion gate).

Same temporal-holdout protocol (fit pre-2024, score on 2024->now). Dixon-Coles is a strict
generalisation of plain Poisson (rho=0 recovers it); the decision is whether it earns the goals
slot in the shipped trio. Deciding evidence on the hold-out:
  - 1X2 log loss / RPS (vs plain Poisson and the other two models),
  - draw calibration (DC should shrink Poisson's draw under-prediction),
  - scoreline log-likelihood (the metric DC directly targets).
The gate is REPORTED, not asserted — promotion is a human call on the numbers.

Run from the project root:  python3 prelim_pred/checkin4.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prelim_elo"))

from dataset import build_samples, temporal_split, CUTOFF                       # noqa: E402
from metrics import log_loss, rps                                              # noqa: E402
from models import (davidson_probs, ordlogit_probs, poisson_probs, dixoncoles_probs,  # noqa: E402
                    score_logprob, fit_davidson, fit_ordlogit, fit_poisson, fit_dixoncoles)


def _score(samples, prob_of_dr):
    """(log_loss, rps) of a dr->probs forecaster over samples."""
    probs = [prob_of_dr(s.dr) for s in samples]
    outcomes = [s.outcome for s in samples]
    return log_loss(probs, outcomes), rps(probs, outcomes)


def _mean_score_logprob(samples, mu, beta, rho):
    """Mean log grid-normalised probability of the actual scoreline (the goals-fit metric)."""
    return sum(score_logprob(s.dr, mu, beta, s.home_score, s.away_score, rho)
               for s in samples) / len(samples)


def main() -> None:
    print("=" * 78)
    print("CHECK-IN 4 — Dixon-Coles vs plain Poisson (promotion gate) + full comparison")
    print("=" * 78)

    samples = build_samples()
    train, test = temporal_split(samples)
    print(f"\n[1] Split (cutoff {CUTOFF}): train {len(train):,} "
          f"({train[0].date}..{train[-1].date})  |  "
          f"test {len(test):,} ({test[0].date}..{test[-1].date})")

    counts = Counter(s.outcome for s in train)
    n = len(train)
    base = (counts[0] / n, counts[1] / n, counts[2] / n)

    nu = fit_davidson(train)
    b, theta = fit_ordlogit(train)
    mu, beta = fit_poisson(train)
    dmu, dbeta, rho = fit_dixoncoles(train)
    print("\n[2] Fits on train:")
    print(f"    Davidson      nu = {nu:.4f}")
    print(f"    OrderedLogit  b = {b:.5f}  theta = {theta:.4f}")
    print(f"    Poisson       mu = {mu:.4f}  beta = {beta:.4f}")
    print(f"    Dixon-Coles   mu = {dmu:.4f}  beta = {dbeta:.4f}  rho = {rho:+.4f}")

    models = [
        ("base-rate", lambda dr: base),
        ("Davidson", lambda dr: davidson_probs(dr, nu)),
        ("OrderedLogit", lambda dr: ordlogit_probs(dr, b, theta)),
        ("Poisson", lambda dr: poisson_probs(dr, mu, beta)),
        ("Dixon-Coles", lambda dr: dixoncoles_probs(dr, dmu, dbeta, rho)),
    ]
    print("\n[3] 1X2 validation (lower is better; TEST is the verdict)")
    print(f"    {'model':<14}{'train LL':>10}{'test LL':>10}{'train RPS':>12}{'test RPS':>11}")
    test_scores = {}
    for name, fn in models:
        tr_s, te_s = _score(train, fn), _score(test, fn)
        test_scores[name] = te_s
        print(f"    {name:<14}{tr_s[0]:>10.4f}{te_s[0]:>10.4f}{tr_s[1]:>12.4f}{te_s[1]:>11.4f}")

    ranked = sorted((te[0], name) for name, te in test_scores.items() if name != "base-rate")
    print("\n[4] Test log-loss ranking:  " + "  <  ".join(f"{nm} ({ll:.4f})" for ll, nm in ranked))

    actual_draw = sum(1 for s in test if s.outcome == 1) / len(test)
    print(f"\n[5] Draw calibration on the hold-out (actual draw rate = {actual_draw:.3f})")
    print(f"    {'model':<14}{'mean predicted P(draw)':>24}{'gap vs actual':>16}")
    for name, fn in models[1:]:
        mean_pred = sum(fn(s.dr)[1] for s in test) / len(test)
        print(f"    {name:<14}{mean_pred:>24.3f}{mean_pred - actual_draw:>+16.3f}")

    print("\n[6] Scoreline fit on the hold-out (mean log P(actual score); higher is better)")
    ll_pois = _mean_score_logprob(test, mu, beta, 0.0)
    ll_dc = _mean_score_logprob(test, dmu, dbeta, rho)
    print(f"    Poisson      {ll_pois:>10.4f}")
    print(f"    Dixon-Coles  {ll_dc:>10.4f}   (delta {ll_dc - ll_pois:+.4f})")

    print("\n[7] PROMOTION GATE — Dixon-Coles vs plain Poisson on the hold-out")
    dc, po = test_scores["Dixon-Coles"], test_scores["Poisson"]
    checks = [
        ("1X2 log loss", dc[0] < po[0], f"{dc[0]:.4f} vs {po[0]:.4f}"),
        ("1X2 RPS", dc[1] < po[1], f"{dc[1]:.4f} vs {po[1]:.4f}"),
        ("scoreline log-prob", ll_dc > ll_pois, f"{ll_dc:.4f} vs {ll_pois:.4f}"),
    ]
    for label, won, detail in checks:
        print(f"    {'WIN ' if won else 'LOSS'}  {label:<20} {detail}")
    verdict = "PROMOTE Dixon-Coles" if all(w for _, w, _ in checks) else "KEEP plain Poisson"
    print(f"    => {verdict}")

    print("\n[8] H / D / A (%) at a few rating gaps:")
    print(f"    {'dr':>5}{'Davidson':>20}{'OrderedLogit':>20}{'Poisson':>20}{'Dixon-Coles':>20}")
    fmt = lambda p: "/".join(f"{100 * x:.1f}" for x in p)  # noqa: E731
    for dr in (0, 100, 282, 426):
        print(f"    {dr:>5}{fmt(davidson_probs(dr, nu)):>20}{fmt(ordlogit_probs(dr, b, theta)):>20}"
              f"{fmt(poisson_probs(dr, mu, beta)):>20}{fmt(dixoncoles_probs(dr, dmu, dbeta, rho)):>20}")

    print("\n[9] Verification")
    _verify(nu, b, theta, mu, beta, dmu, dbeta, rho, test_scores)
    print("\nAll checks passed.")


def _verify(nu, b, theta, mu, beta, dmu, dbeta, rho, test_scores) -> None:
    forecasters = (lambda dr: davidson_probs(dr, nu),
                   lambda dr: ordlogit_probs(dr, b, theta),
                   lambda dr: poisson_probs(dr, mu, beta),
                   lambda dr: dixoncoles_probs(dr, dmu, dbeta, rho))

    for fn in forecasters:
        for dr in range(-800, 801, 50):
            p = fn(dr)
            assert abs(sum(p) - 1.0) < 1e-9, (dr, p)
            assert all(x >= -1e-12 for x in p), (dr, p)
    print("    all four: probabilities sum to 1 and stay non-negative over dr [-800,800]  OK")

    for fn in forecasters:
        assert abs(fn(0)[0] - fn(0)[2]) < 1e-9, fn(0)              # symmetric at dr=0
        prev = -1.0
        for dr in range(-800, 801, 25):
            ph = fn(dr)[0]
            assert ph > prev, (dr, ph, prev)                      # P(home) strictly increasing
            prev = ph
    print("    all four: symmetric at dr=0 and P(home) strictly increasing in dr  OK")

    # Dixon-Coles nests plain Poisson: rho=0 must reproduce poisson_probs exactly.
    for dr in (-300, 0, 150, 400):
        a = dixoncoles_probs(dr, mu, beta, 0.0)
        c = poisson_probs(dr, mu, beta)
        assert max(abs(x - y) for x, y in zip(a, c)) < 1e-12, (dr, a, c)
    print("    Dixon-Coles at rho=0 reproduces plain Poisson exactly (nesting)  OK")

    for name in ("Davidson", "OrderedLogit", "Poisson", "Dixon-Coles"):
        assert test_scores[name][0] < test_scores["base-rate"][0], name
        assert test_scores[name][1] < test_scores["base-rate"][1], name
    print("    all four beat the base-rate floor out-of-sample (log loss and RPS)  OK")


if __name__ == "__main__":
    main()
