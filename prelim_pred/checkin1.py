"""Check-in 1: scaffold + Davidson, fit on a temporal split and validated out-of-sample.

Pipeline: replay -> (dr, outcome) samples -> split at 2024-01-01 -> fit Davidson's
nu on the TRAIN years only -> score log loss / RPS on the never-seen TEST years.
The yardstick is a base-rate forecaster (predict the historical average H/D/A every
match); Davidson must beat it out-of-sample, which is what "the rating signal predicts"
means here. Also reports the We-drift and the current 1X2 for every pending group game.

Run from the project root:  python3 prelim_pred/checkin1.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prelim_elo"))

from prepare import load_and_prepare        # noqa: E402
from rating import win_expectancy, HOME_ADVANTAGE   # noqa: E402
from engine import run                        # noqa: E402

from dataset import build_samples, temporal_split, CUTOFF      # noqa: E402
from metrics import log_loss, rps                              # noqa: E402
from models import davidson_probs, expected_score, we_drift, fit_davidson  # noqa: E402


def _score(samples, prob_of_dr):
    """(log_loss, rps) of a dr->probs forecaster over samples."""
    probs = [prob_of_dr(s.dr) for s in samples]
    outcomes = [s.outcome for s in samples]
    return log_loss(probs, outcomes), rps(probs, outcomes)


def _fmt_pct(p):
    return f"{100 * p:5.1f}%"


def main() -> None:
    print("=" * 78)
    print("CHECK-IN 1 — Davidson 1X2: scaffold + temporal-holdout validation")
    print("=" * 78)

    # --- 1) dataset & split -------------------------------------------------
    samples = build_samples()
    train, test = temporal_split(samples)
    n_tr, n_te = len(train), len(test)
    print(f"\n[1] Dataset & split (cutoff {CUTOFF})")
    print(f"    all played matches : {len(samples):,}")
    print(f"    train (before)     : {n_tr:,}   {train[0].date} .. {train[-1].date}")
    print(f"    test  (on/after)   : {n_te:,}   {test[0].date} .. {test[-1].date}")

    tr_counts = Counter(s.outcome for s in train)
    base = (tr_counts[0] / n_tr, tr_counts[1] / n_tr, tr_counts[2] / n_tr)
    print(f"    train base rate    : home {_fmt_pct(base[0])}  draw {_fmt_pct(base[1])}"
          f"  away {_fmt_pct(base[2])}")

    # --- 2) fit Davidson on TRAIN only -------------------------------------
    nu = fit_davidson(train)
    print(f"\n[2] Davidson fit on train  ->  nu = {nu:.4f}  (one parameter, scale pinned to 400)")

    # --- 3) held-out validation --------------------------------------------
    dav = lambda dr: davidson_probs(dr, nu)            # noqa: E731
    const = lambda dr: base                            # noqa: E731  (base-rate ignores dr)
    dav_tr = _score(train, dav)
    dav_te = _score(test, dav)
    base_tr = _score(train, const)
    base_te = _score(test, const)

    print(f"\n[3] Validation  (lower is better; TEST is the verdict)")
    print(f"    {'model':<12}{'train LL':>10}{'test LL':>10}{'train RPS':>12}{'test RPS':>11}")
    print(f"    {'base-rate':<12}{base_tr[0]:>10.4f}{base_te[0]:>10.4f}"
          f"{base_tr[1]:>12.4f}{base_te[1]:>11.4f}")
    print(f"    {'Davidson':<12}{dav_tr[0]:>10.4f}{dav_te[0]:>10.4f}"
          f"{dav_tr[1]:>12.4f}{dav_te[1]:>11.4f}")
    ll_gain = 100 * (base_te[0] - dav_te[0]) / base_te[0]
    rps_gain = 100 * (base_te[1] - dav_te[1]) / base_te[1]
    print(f"    Davidson improves on the base-rate floor out-of-sample by "
          f"{ll_gain:.1f}% log loss, {rps_gain:.1f}% RPS.")
    print(f"    train vs test LL gap = {abs(dav_tr[0] - dav_te[0]):.4f} "
          f"(small => the 1-parameter fit is not overfitting).")

    # --- 4) We-drift report (D5) -------------------------------------------
    print(f"\n[4] We-drift: Davidson's implied expected score vs Elo's We "
          f"(equal only at dr=0)")
    print(f"    {'dr':>5}{'Elo We':>10}{'Davidson E[score]':>20}{'drift':>10}")
    for dr in (0, 50, 100, 200, 300, 426, 600):
        es = expected_score(davidson_probs(dr, nu))
        print(f"    {dr:>5}{win_expectancy(dr):>10.4f}{es:>20.4f}{es - win_expectancy(dr):>+10.4f}")
    mean_abs_drift = sum(abs(we_drift(s.dr, nu)) for s in test) / n_te
    print(f"    mean |drift| over the test set = {mean_abs_drift:.4f}")

    # --- 5) current predictions for the pending group fixtures -------------
    ratings, _, _, _ = run()
    _, fixtures = load_and_prepare()
    print(f"\n[5] Current Davidson 1X2 for the {len(fixtures)} pending group fixtures")
    print(f"    {'date':<11}{'match':<34}{'dr':>5}  {'P(H)':>6}{'P(D)':>6}{'P(A)':>6}"
          f"   fair odds H/D/A")
    for m in sorted(fixtures, key=lambda m: (m.date, m.home)):
        rh, ra = ratings[m.home], ratings[m.away]
        dr = rh - ra + (0 if m.neutral else HOME_ADVANTAGE)
        pH, pD, pA = davidson_probs(dr, nu)
        venue = "" if m.neutral else " (H)"
        match = f"{m.home} v {m.away}{venue}"
        print(f"    {m.date:<11}{match:<34}{dr:>5}  {_fmt_pct(pH)}{_fmt_pct(pD)}{_fmt_pct(pA)}"
              f"   {1/pH:>4.2f}/{1/pD:>5.2f}/{1/pA:>6.2f}")

    # --- 6) verification ----------------------------------------------------
    print(f"\n[6] Verification")
    _verify(nu, dav_te, base_te)
    print("\nAll checks passed.")


def _verify(nu, dav_te, base_te) -> None:
    # probabilities are a valid distribution across the dr range
    for dr in range(-800, 801, 50):
        p = davidson_probs(dr, nu)
        assert abs(sum(p) - 1.0) < 1e-12, (dr, p)
        assert all(x >= 0.0 for x in p), (dr, p)
    print("    probabilities sum to 1 and stay non-negative over dr in [-800, 800]  OK")

    # symmetry and We-consistency at dr = 0
    p0 = davidson_probs(0, nu)
    assert abs(p0[0] - p0[2]) < 1e-12, p0
    assert abs(expected_score(p0) - 0.5) < 1e-12, p0
    assert abs(we_drift(0, nu)) < 1e-12
    print("    at dr=0: P(home)=P(away), E[score]=0.500=We(0), drift=0  OK")

    # P(home) strictly increases with dr (favourite gets likelier)
    prev = -1.0
    for dr in range(-800, 801, 25):
        ph = davidson_probs(dr, nu)[0]
        assert ph > prev, (dr, ph, prev)
        prev = ph
    print("    P(home) strictly increases with dr  OK")

    # the validation bar: Davidson beats the base-rate floor on the held-out test
    assert dav_te[0] < base_te[0], (dav_te[0], base_te[0])
    assert dav_te[1] < base_te[1], (dav_te[1], base_te[1])
    print("    Davidson beats base-rate out-of-sample on BOTH log loss and RPS  OK")


if __name__ == "__main__":
    main()
