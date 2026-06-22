"""Export rating data as JSON for the web frontend.

Writes one current-table file (and, for systems with history, one yearly time-series
file) per rating system, plus a manifest. Adding a future rating system = generate its
two files and append an entry to the manifest; the frontend is manifest-driven.

FIFA is included as a labelled reference benchmark only (see fifa_rankings.md); it is
never used by the model.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from prepare import load_and_prepare
from engine import run, PROVISIONAL_MATCHES
from output import wc2026_teams

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "frontend" / "data"
FIFA_MD = BASE / "fifa_rankings.md"

# FIFA prints some teams under different names; alias the WC-relevant ones to dataset names
# so World Cup membership lines up across systems.
FIFA_ALIASES = {
    "USA": "United States", "IR Iran": "Iran", "Türkiye": "Turkey",
    "Korea Republic": "South Korea", "Côte d'Ivoire": "Ivory Coast",
    "Czechia": "Czech Republic", "Congo DR": "DR Congo", "Cabo Verde": "Cape Verde",
}


def elo_current(ratings, counts, last_date, wc):
    rows = sorted(ratings.items(), key=lambda kv: kv[1], reverse=True)
    return [{"rank": i, "team": t, "rating": r, "games": counts[t],
             "provisional": counts[t] < PROVISIONAL_MATCHES,
             "last_match": last_date[t], "wc2026": t in wc}
            for i, (t, r) in enumerate(rows, 1)]


def yearly_history(history):
    """Down-sample each team's per-match history to one point per calendar year."""
    out = {}
    for team, pts in history.items():
        by_year = {}
        for date, rating in pts:
            by_year[int(date[:4])] = rating  # last rating in the year wins
        out[team] = sorted([y, r] for y, r in by_year.items())
    return out


def parse_fifa(wc):
    pat = re.compile(r"^\s*(\d+)\.\s+(.+?)\s+—\s+([\d.]+)\s+\(([^)]+)\)")
    rows = []
    for line in FIFA_MD.read_text(encoding="utf-8").splitlines():
        m = pat.match(line)
        if not m:
            continue
        rank, team, points, conf = m.groups()
        rows.append({"rank": int(rank), "team": team, "points": float(points),
                     "confederation": conf, "wc2026": FIFA_ALIASES.get(team, team) in wc})
    return rows


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    played, fixtures = load_and_prepare()
    wc = wc2026_teams(played, fixtures)
    ratings, counts, last_date, _, history = run(record_history=True)

    (DATA / "prelim_elo_current.json").write_text(
        json.dumps(elo_current(ratings, counts, last_date, wc)), encoding="utf-8")
    (DATA / "prelim_elo_history.json").write_text(
        json.dumps(yearly_history(history)), encoding="utf-8")
    (DATA / "fifa_current.json").write_text(
        json.dumps(parse_fifa(wc)), encoding="utf-8")

    manifest = {
        "wc2026": sorted(wc),
        "systems": [
            {"id": "prelim_elo", "label": "Preliminary Elo", "kind": "elo", "hasHistory": True},
            {"id": "fifa", "label": "FIFA World Ranking (reference only)",
             "kind": "fifa", "hasHistory": False},
        ],
    }
    (DATA / "systems.json").write_text(json.dumps(manifest), encoding="utf-8")

    print(f"Wrote JSON to {DATA}")
    for f in sorted(DATA.glob("*.json")):
        print(f"  {f.name:<28} {f.stat().st_size:>8,} bytes")
    print(f"systems: {[s['id'] for s in manifest['systems']]}; WC teams: {len(wc)}")


if __name__ == "__main__":
    main()
