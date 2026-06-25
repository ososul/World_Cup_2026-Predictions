"""Check-in 3: add the independent-Poisson model; three-way temporal-holdout validation.

Same protocol (fit pre-2024, score log loss / RPS on the 2024->now hold-out, beat base-rate),
now comparing Davidson, ordered logistic, and Poisson. Adds a DRAW-CALIBRATION diagnostic —
the deciding evidence for whether plain Poisson needs the Dixon-Coles low-score correction (D10).

Run from the project root:  python3 prelim_pred/checkin3.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prelim_elo"))

from dataset import build_samples, temporal_split, CUTOFF                       # noqa: E402
from metrics import log_loss, rps                                               # noqa: E402
from models import (davidson_probs, ordlogit_probs, poisson_probs, poisson_lambdas,  # noqa: E402
                    fit_davidson, fit_ordlogit, fit_poisson)


def _score(samples, prob_of_dr):
    """(log_loss, rps) of a dr->probs forecaster over samples."""
    probs = [prob_of_dr(s.dr) for s in samples]
    outcomes = [s.outcome for s in samples]
    return log_loss(probs, outcomes), rps(probs, outcomes)


def main() -> None:
    print("=" * 78)
    print("CHECK-IN 3 — Poisson vs Davidson vs Ordered logistic: holdout validation")
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
    print("\n[2] Fits on train:")
    print(f"    Davidson      nu = {nu:.4f}")
    print(f"    OrderedLogit  b = {b:.5f}  theta = {theta:.4f}")
    print(f"    Poisson       mu = {mu:.4f}  beta = {beta:.4f}  (fit to scorelines)")

    models = [
        ("base-rate", lambda dr: base),
        ("Davidson", lambda dr: davidson_probs(dr, nu)),
        ("OrderedLogit", lambda dr: ordlogit_probs(dr, b, theta)),
        ("Poisson", lambda dr: poisson_probs(dr, mu, beta)),
    ]
    print("\n[3] Validation (lower is better; TEST is the verdict)")
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

    print("\n[6] H / D / A (%) at a few rating gaps, plus Poisson expected goals:")
    print(f"    {'dr':>5}{'Davidson':>22}{'OrderedLogit':>22}{'Poisson':>22}{'Poisson xG':>14}")
    fmt = lambda p: "/".join(f"{100 * x:.1f}" for x in p)  # noqa: E731
    for dr in (0, 100, 282, 426):
        lh, la = poisson_lambdas(dr, mu, beta)
        print(f"    {dr:>5}{fmt(davidson_probs(dr, nu)):>22}{fmt(ordlogit_probs(dr, b, theta)):>22}"
              f"{fmt(poisson_probs(dr, mu, beta)):>22}{f'{lh:.2f}-{la:.2f}':>14}")

    print("\n[7] Verification")
    _verify(nu, b, theta, mu, beta, test_scores)
    print("\nAll checks passed.")


def _verify(nu, b, theta, mu, beta, test_scores) -> None:
    forecasters = (lambda dr: davidson_probs(dr, nu),
                   lambda dr: ordlogit_probs(dr, b, theta),
                   lambda dr: poisson_probs(dr, mu, beta))

    for fn in forecasters:
        for dr in range(-800, 801, 50):
            p = fn(dr)
            assert abs(sum(p) - 1.0) < 1e-9, (dr, p)
            assert all(x >= -1e-12 for x in p), (dr, p)
    print("    all three: probabilities sum to 1 and stay non-negative over dr [-800,800]  OK")

    for fn in forecasters:
        assert abs(fn(0)[0] - fn(0)[2]) < 1e-9, fn(0)              # symmetric at dr=0
        prev = -1.0
        for dr in range(-800, 801, 25):
            ph = fn(dr)[0]
            assert ph > prev, (dr, ph, prev)                      # P(home) strictly increasing
            prev = ph
    print("    all three: symmetric at dr=0 and P(home) strictly increasing in dr  OK")

    for name in ("Davidson", "OrderedLogit", "Poisson"):
        assert test_scores[name][0] < test_scores["base-rate"][0], name
        assert test_scores[name][1] < test_scores["base-rate"][1], name
    print("    all three beat the base-rate floor out-of-sample (log loss and RPS)  OK")


if __name__ == "__main__":
    main()
