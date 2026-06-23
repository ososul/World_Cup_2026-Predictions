"""Prediction layer — build the modelling dataset from the prelim Elo engine.

Replays every played match in chronological order (the same loop engine.run uses)
and records each match's PRE-MATCH rating difference dr — with the engine's H=100
home-advantage convention — alongside the realised result. This (dr -> outcome)
table is what every outcome model is fit and tested on. It consumes the engine's
math (match_deltas) rather than re-deriving it; the only reason we re-run the loop
here is that engine.run does not expose the per-match pre-match dr.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prelim_elo"))

from prepare import load_and_prepare              # noqa: E402
from rating import match_deltas, HOME_ADVANTAGE   # noqa: E402
from engine import INITIAL                         # noqa: E402

CUTOFF = "2024-01-01"  # temporal split: fit strictly before, test on/after


@dataclass(frozen=True)
class Sample:
    date: str
    home: str
    away: str
    neutral: bool
    dr: int            # pre-match  R_home - R_away + H   (H = 0 if neutral else 100)
    home_score: int
    away_score: int
    outcome: int       # 0 home win, 1 draw, 2 away win


def _outcome(home_score: int, away_score: int) -> int:
    if home_score > away_score:
        return 0
    if home_score == away_score:
        return 1
    return 2


def build_samples() -> list[Sample]:
    """One Sample per played match, carrying its pre-match dr and result."""
    played, _ = load_and_prepare()
    ratings: dict[str, int] = {}
    samples: list[Sample] = []
    for m in played:
        rh = ratings.get(m.home, INITIAL)
        ra = ratings.get(m.away, INITIAL)
        h = 0 if m.neutral else HOME_ADVANTAGE
        samples.append(Sample(m.date, m.home, m.away, m.neutral,
                              rh - ra + h, m.home_score, m.away_score,
                              _outcome(m.home_score, m.away_score)))
        dh, da = match_deltas(rh, ra, m.neutral, m.k_eff, m.home_score, m.away_score)
        ratings[m.home] = rh + dh
        ratings[m.away] = ra + da
    return samples


def temporal_split(samples: list[Sample], cutoff: str = CUTOFF):
    """(train, test): train = matches strictly before cutoff, test = on/after."""
    train = [s for s in samples if s.date < cutoff]
    test = [s for s in samples if s.date >= cutoff]
    return train, test
