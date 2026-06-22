"""Preliminary Elo System (spec: PreliminaryEloSystem.md) - Step 2: load & prepare.

Splits played matches (used to compute ratings) from the unplayed World Cup
fixtures (the predict-set), sorts chronologically, and attaches each match's
tournament weight K_base plus the goal-difference multiplier G and K_eff.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "data_set_copy" / "results.csv"
TIERS = BASE / "tournament_tiers.json"
DEFAULT_K = 30  # unmapped tournament -> "other tournament" tier


@dataclass
class Match:
    date: str
    home: str
    away: str
    neutral: bool
    tournament: str
    k_base: int
    home_score: int | None = None
    away_score: int | None = None
    g: float | None = None       # goal-difference multiplier
    k_eff: float | None = None   # k_base * g


def goal_multiplier(margin: int) -> float:
    n = abs(margin)
    if n <= 1:
        return 1.0
    if n == 2:
        return 1.5
    if n == 3:
        return 1.75
    return 1.75 + (n - 3) / 8


def _parse_neutral(value: str) -> bool:
    if value == "TRUE":
        return True
    if value == "FALSE":
        return False
    raise ValueError(f"unexpected neutral value: {value!r}")


def load_and_prepare() -> tuple[list[Match], list[Match]]:
    """Return (played, fixtures): played sorted chronologically, fixtures = unplayed rows."""
    k_table = json.loads(TIERS.read_text(encoding="utf-8"))

    played: list[Match] = []
    fixtures: list[Match] = []
    with RESULTS.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tournament = row["tournament"]
            m = Match(
                date=row["date"],
                home=row["home_team"],
                away=row["away_team"],
                neutral=_parse_neutral(row["neutral"]),
                tournament=tournament,
                k_base=k_table.get(tournament, DEFAULT_K),
            )
            hs, as_ = row["home_score"], row["away_score"]
            if hs == "NA" or as_ == "NA":
                if hs != "NA" or as_ != "NA":
                    raise ValueError(f"half-missing score: {row}")
                fixtures.append(m)
            else:
                m.home_score, m.away_score = int(hs), int(as_)
                m.g = goal_multiplier(m.home_score - m.away_score)
                m.k_eff = m.k_base * m.g
                played.append(m)

    played.sort(key=lambda m: m.date)  # stable sort: same-day ties keep file order
    return played, fixtures


def _verify() -> None:
    played, fixtures = load_and_prepare()
    k_table = json.loads(TIERS.read_text(encoding="utf-8"))

    total_rows = sum(1 for _ in csv.DictReader(RESULTS.open(newline="", encoding="utf-8")))
    tournaments = {m.tournament for m in played} | {m.tournament for m in fixtures}
    unmapped = sorted(t for t in tournaments if t not in k_table)
    dates = [m.date for m in played]

    print("=== Step 2: load & prepare ===")
    print(f"CSV rows (data):      {total_rows}")
    print(f"  played (scored):    {len(played)}")
    print(f"  fixtures (NA):      {len(fixtures)}")
    print(f"  sum check:          {'OK' if len(played) + len(fixtures) == total_rows else 'MISMATCH'}")
    print(f"Tournament coverage:  {len(tournaments) - len(unmapped)}/{len(tournaments)} mapped, "
          f"{len(unmapped)} fell to default" + (f" -> {unmapped}" if unmapped else ""))
    print(f"Chronological order:  {'OK (non-decreasing)' if dates == sorted(dates) else 'NOT SORTED'}")
    print(f"Played date range:    {dates[0]} .. {dates[-1]}")

    non_wc_fixtures = [m for m in fixtures if m.tournament != "FIFA World Cup"]
    fx_dates = sorted(m.date for m in fixtures)
    print(f"Fixtures (predict-set): all FIFA World Cup = {not non_wc_fixtures}, "
          f"{fx_dates[0]} .. {fx_dates[-1]}")

    print("Sample K_eff (played WC 2026):")
    for m in sorted((m for m in played if m.tournament == "FIFA World Cup" and m.date >= "2026"),
                    key=lambda m: m.date)[:4]:
        print(f"  {m.date} {m.home} {m.home_score}-{m.away_score} {m.away}  "
              f"k_base={m.k_base} G={m.g} k_eff={m.k_eff:.2f}")


if __name__ == "__main__":
    _verify()
