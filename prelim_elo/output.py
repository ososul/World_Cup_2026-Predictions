"""Preliminary Elo System (spec: PreliminaryEloSystem.md) - Step 5: output & views.

Writes the current rating table to CSV and prints the World Cup 2026 field ranked
by current rating. Confirms every WC team name resolves to a rating.
"""
from __future__ import annotations

import csv
from pathlib import Path

from prepare import load_and_prepare
from engine import run, PROVISIONAL_MATCHES

OUT = Path(__file__).resolve().parent.parent / "current_ratings.csv"


def wc2026_teams(played, fixtures) -> set[str]:
    """The World Cup 2026 field = every team in a 2026 WC match (played or upcoming fixture)."""
    wc_matches = list(fixtures) + [m for m in played
                                   if m.tournament == "FIFA World Cup" and m.date >= "2026"]
    return {m.home for m in wc_matches} | {m.away for m in wc_matches}


def write_csv(ratings, counts, last_date) -> None:
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "team", "rating", "games", "provisional", "last_match"])
        for rank, (team, r) in enumerate(
                sorted(ratings.items(), key=lambda kv: kv[1], reverse=True), 1):
            w.writerow([rank, team, r, counts[team],
                        counts[team] < PROVISIONAL_MATCHES, last_date[team]])


def _run() -> None:
    print("=== Step 5: output & views ===")
    played, fixtures = load_and_prepare()
    ratings, counts, last_date, _ = run()

    write_csv(ratings, counts, last_date)
    print(f"Wrote full table -> {OUT.name}  ({len(ratings)} teams)")

    wc = wc2026_teams(played, fixtures)
    missing = sorted(t for t in wc if t not in ratings)
    print(f"WC 2026 field:    {len(wc)} teams; coverage {len(wc) - len(missing)}/{len(wc)}"
          + (f"  MISSING {missing}" if missing else "  (all resolve)"))
    assert not missing, f"WC teams without a rating: {missing}"

    print("\nWorld Cup 2026 - current Preliminary Elo:")
    for i, t in enumerate(sorted(wc, key=lambda t: ratings[t], reverse=True), 1):
        prov = "*" if counts[t] < PROVISIONAL_MATCHES else " "
        print(f"  {i:>2}. {t:<24} {ratings[t]:>5} {prov} ({counts[t]} games)")


if __name__ == "__main__":
    _run()
