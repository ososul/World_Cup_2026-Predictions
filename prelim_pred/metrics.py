"""Proper scoring rules for 1X2 probability forecasts (pure math, no state).

Both are PROPER (minimised in expectation only by honest probabilities) and
lower-is-better, so they grade calibration rather than win/loss accuracy:

  log_loss : mean negative log-likelihood (natural log) of the realised outcomes.
             Primary judge, and the objective the Davidson fit minimises.
  rps      : ranked probability score for the ORDERED outcomes home < draw < away.
             Secondary judge; penalises being far in the ordering more than near.

`probs` is any iterable of (p_home, p_draw, p_away); `outcomes` a same-length
sequence of 0/1/2 codes (home/draw/away).
"""
from __future__ import annotations

import math

_FLOOR = 1e-15  # clamp a probability away from 0 before taking its log


def log_loss(probs, outcomes) -> float:
    total = 0.0
    for p, oc in zip(probs, outcomes):
        total += -math.log(max(p[oc], _FLOOR))
    return total / len(outcomes)


def rps(probs, outcomes) -> float:
    total = 0.0
    for (p_home, p_draw, _), oc in zip(probs, outcomes):
        cum_pred1 = p_home              # P(home)
        cum_pred2 = p_home + p_draw     # P(home or draw)
        cum_obs1 = 1.0 if oc == 0 else 0.0
        cum_obs2 = 1.0 if oc <= 1 else 0.0
        total += 0.5 * ((cum_pred1 - cum_obs1) ** 2 + (cum_pred2 - cum_obs2) ** 2)
    return total / len(outcomes)
