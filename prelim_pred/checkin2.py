"""Check-in 2: add the ordered-logistic model and validate it head-to-head vs Davidson.

Same temporal-holdout protocol as check-in 1 (fit on pre-2024, score log loss / RPS on the
2024->now hold-out, beat the base-rate floor). Reports both models side by side so we can
see which generalises better out-of-sample and where they differ.

Run from the project root:  python3 prelim_pred/checkin2.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prelim_elo"))

from dataset import build_samples, temporal_split, CUTOFF                    # noqa: E402
from metrics import log_loss, rps                                            # noqa: E402
from models import davidson_probs, ordlogit_probs, fit_davidson, fit_ordlogit  # noqa: E402


def _score(samples, prob_of_dr):
    """(log_loss, rps) of a dr->probs forecaster over samples."""
    probs = [prob_of_dr(s.dr) for s in samples]
    outcomes = [s.outcome for s in samples]
    return log_loss(probs, outcomes), rps(probs, outcomes)


def main() -> None:
    print("=" * 78)
    print("CHECK-IN 2 — Ordered logistic vs Davidson: temporal-holdout validation")
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
    print("\n[2] Fits on train:")
    print(f"    Davidson      nu = {nu:.4f}                  (scale pinned to 400)")
    print(f"    OrderedLogit  b = {b:.5f}  theta = {theta:.4f}  (scale free)")

    models = [
        ("base-rate", lambda dr: base),
        ("Davidson", lambda dr: davidson_probs(dr, nu)),
        ("OrderedLogit", lambda dr: ordlogit_probs(dr, b, theta)),
    ]
    print("\n[3] Validation (lower is better; TEST is the verdict)")
    print(f"    {'model':<14}{'train LL':>10}{'test LL':>10}{'train RPS':>12}{'test RPS':>11}")
    test_scores = {}
    for name, fn in models:
        tr_s, te_s = _score(train, fn), _score(test, fn)
        test_scores[name] = te_s
        print(f"    {name:<14}{tr_s[0]:>10.4f}{te_s[0]:>10.4f}{tr_s[1]:>12.4f}{te_s[1]:>11.4f}")

    d, o = test_scores["Davidson"], test_scores["OrderedLogit"]
    ll_win = "OrderedLogit" if o[0] < d[0] else "Davidson"
    rps_win = "OrderedLogit" if o[1] < d[1] else "Davidson"
    print(f"\n[4] Head-to-head on the hold-out:")
    print(f"    log loss -> {ll_win} wins ({min(o[0], d[0]):.4f} vs {max(o[0], d[0]):.4f})")
    print(f"    RPS      -> {rps_win} wins ({min(o[1], d[1]):.4f} vs {max(o[1], d[1]):.4f})")

    print("\n[5] Where they differ — H / D / A (%) at a few rating gaps:")
    print(f"    {'dr':>5}{'Davidson':>26}{'OrderedLogit':>26}")
    fmt = lambda p: "/".join(f"{100 * x:.1f}" for x in p)  # noqa: E731
    for dr in (0, 100, 282, 426):
        print(f"    {dr:>5}{fmt(davidson_probs(dr, nu)):>26}{fmt(ordlogit_probs(dr, b, theta)):>26}")

    print("\n[6] Verification")
    _verify(nu, b, theta, test_scores)
    print("\nAll checks passed.")


def _verify(nu, b, theta, test_scores) -> None:
    forecasters = (lambda dr: davidson_probs(dr, nu), lambda dr: ordlogit_probs(dr, b, theta))

    for fn in forecasters:
        for dr in range(-800, 801, 50):
            p = fn(dr)
            assert abs(sum(p) - 1.0) < 1e-12, (dr, p)
            assert all(x >= -1e-12 for x in p), (dr, p)
    print("    both models: probabilities sum to 1 and stay non-negative over dr [-800,800]  OK")

    for fn in forecasters:
        assert abs(fn(0)[0] - fn(0)[2]) < 1e-12, fn(0)          # symmetric at dr=0
        prev = -1.0
        for dr in range(-800, 801, 25):
            ph = fn(dr)[0]
            assert ph > prev, (dr, ph, prev)                    # P(home) strictly increasing
            prev = ph
    print("    both models: symmetric at dr=0 and P(home) strictly increasing in dr  OK")

    for name in ("Davidson", "OrderedLogit"):
        assert test_scores[name][0] < test_scores["base-rate"][0], name
        assert test_scores[name][1] < test_scores["base-rate"][1], name
    print("    both models beat the base-rate floor out-of-sample on log loss and RPS  OK")


if __name__ == "__main__":
    main()
