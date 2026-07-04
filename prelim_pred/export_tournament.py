"""Export the tournament projection for the frontend (groups.json + bracket.json).

Runs the full pipeline from tournament.py — verified inputs, group tallies,
knockout resolution, fresh production fits (all played matches; deterministic,
same numbers as predict.json on the same data), per-match quotes and the exact
DP — then writes the two files the frontend reads through web/lib/data.ts.
Every parameter used is recorded in bracket.json for transparency. Re-run after
appending knockout results to results.csv (+ shootouts.csv for a pens game):
ratings, fits and the DP all re-condition automatically.

Match entries: `probs` + `scorelines` whenever both teams are known (for played
matches these are as-of-now quotes off current ratings, not historical pre-match
odds); `candidates` (per-slot arrival distributions, ensemble DP) whenever a
slot is still unresolved. `reach` covers all four model ids incl. "ensemble".

    python3 prelim_pred/export_tournament.py
      -> web/public/data/groups.json, web/public/data/bracket.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prelim_elo"))
sys.path.insert(0, str(ROOT / "prelim_pred"))

from prepare import load_and_prepare      # noqa: E402
from engine import run                    # noqa: E402
from rating import HOME_ADVANTAGE         # noqa: E402
from dataset import build_samples         # noqa: E402
from tournament import (                  # noqa: E402
    MODEL_IDS, PENS_HOME,
    load_groups, load_bracket_spec, load_shootout_winners,
    wc2026_rows, split_group_knockout, group_tables, validate_inputs,
    resolve_bracket, validate_played_conventions,
    fit_all, match_quote, dc_scorelines, project_all,
)

DATA = ROOT / "web" / "public" / "data"
ALL_MODELS = (*MODEL_IDS, "ensemble")


def build_groups_json(tables: dict, generated: str) -> dict:
    return {"generated": generated, "groups": [
        {"id": gid,
         "table": t["table"],
         "matches": [{"date": m.date, "home": m.home, "away": m.away,
                      "homeScore": m.home_score, "awayScore": m.away_score}
                     for m in t["matches"]]}
        for gid, t in sorted(tables.items())]}


def build_bracket_json(resolved: dict, projs: dict, ratings: dict, fits: dict,
                       generated: str) -> dict:
    matches = []
    for no, m in sorted(resolved.items()):
        entry = {"match": no, "round": m["round"], "date": m["date"],
                 "venueCountry": m["venueCountry"],
                 "homeSlot": m["homeSlot"], "awaySlot": m["awaySlot"],
                 "homeTeam": m["homeTeam"], "awayTeam": m["awayTeam"],
                 "status": m["status"], "result": m["result"],
                 "probs": None, "scorelines": None, "candidates": None}
        if m["homeTeam"] and m["awayTeam"]:
            q = match_quote(m["homeTeam"], m["awayTeam"], m["venueCountry"],
                            ratings, fits)
            entry["probs"] = {mid: {"p90": [round(p, 5) for p in mq["p90"]],
                                    "et": [round(p, 5) for p in mq["et"]],
                                    "pensWin": mq["pensWin"],
                                    "advHome": round(mq["advHome"], 5)}
                              for mid, mq in q.items()}
            entry["scorelines"] = [
                [s, round(p, 5)] for s, p in
                dc_scorelines(m["homeTeam"], m["awayTeam"], m["venueCountry"],
                              ratings, fits)]
        else:
            slots = projs["ensemble"]["slots"][no]
            entry["candidates"] = {
                side: [{"team": t, "p": round(p, 5)}
                       for t, p in sorted(slots[side].items(),
                                          key=lambda kv: -kv[1])]
                for side in ("home", "away")}
        matches.append(entry)

    dav, ol, dc, po = (fits[k] for k in ("davidson", "ordlogit",
                                         "dixoncoles", "poisson"))
    return {
        "ratingSystem": "prelim_elo",
        "homeAdvantage": HOME_ADVANTAGE,
        "generated": generated,
        "models": [
            {"id": "davidson", "label": "Davidson (Preliminary Elo)",
             "params": {"nu": round(dav["nu"], 5)}},
            {"id": "ordlogit", "label": "Ordered logistic (Preliminary Elo)",
             "params": {"b": round(ol["b"], 6), "theta": round(ol["theta"], 5)}},
            {"id": "dixoncoles", "label": "Dixon-Coles (Preliminary Elo)",
             "params": {"mu": round(dc["mu"], 5), "beta": round(dc["beta"], 5),
                        "rho": round(dc["rho"], 5)}},
            {"id": "ensemble", "label": "Ensemble (model average)", "params": {}},
        ],
        "resolution": {"muPois": round(po["mu"], 5), "betaPois": round(po["beta"], 5),
                       "pens": PENS_HOME},
        "matches": matches,
        "reach": {mid: {team: {k: round(v, 5) for k, v in r.items()}
                        for team, r in sorted(projs[mid]["reach"].items())}
                  for mid in ALL_MODELS},
    }


def _verify_exports(groups_path: Path, bracket_path: Path) -> None:
    """Reload the written files and check shape, counts and coverage."""
    g = json.loads(groups_path.read_text(encoding="utf-8"))
    b = json.loads(bracket_path.read_text(encoding="utf-8"))

    assert [grp["id"] for grp in g["groups"]] == list("ABCDEFGHIJKL")
    assert all(len(grp["table"]) == 4 and len(grp["matches"]) == 6
               for grp in g["groups"])
    quals = [r["qualified"] for grp in g["groups"] for r in grp["table"]]
    assert quals.count("direct") == 24 and quals.count("third") == 8
    row_keys = {"pos", "team", "w", "d", "l", "gf", "ga", "gd", "pts", "qualified"}
    assert all(set(r) == row_keys for grp in g["groups"] for r in grp["table"])

    assert [m["match"] for m in b["matches"]] == list(range(73, 105))
    assert [m["id"] for m in b["models"]] == list(ALL_MODELS)
    assert set(b["resolution"]) == {"muPois", "betaPois", "pens"}
    for m in b["matches"]:
        both = bool(m["homeTeam"] and m["awayTeam"])
        assert (m["probs"] is not None) == both, m["match"]
        assert (m["scorelines"] is not None) == both, m["match"]
        assert (m["candidates"] is not None) == (not both), m["match"]
        assert (m["result"] is not None) == (m["status"] == "played"), m["match"]
        if both:
            assert set(m["probs"]) == set(ALL_MODELS)
        else:
            for side in ("home", "away"):
                total = sum(c["p"] for c in m["candidates"][side])
                assert abs(total - 1.0) < 1e-3, (m["match"], side)

    field = {"r16": 16.0, "qf": 8.0, "sf": 4.0, "final": 2.0, "champion": 1.0}
    assert set(b["reach"]) == set(ALL_MODELS)
    for mid, reach in b["reach"].items():
        assert len(reach) == 32, mid
        for key, tot in field.items():
            got = sum(r[key] for r in reach.values())
            assert abs(got - tot) < 1e-3, (mid, key, got)

    # a pre-R16 export: every R32 advHome must equal the team's exported r16 reach
    for m in b["matches"]:
        if m["round"] == "R32" and m["status"] == "scheduled":
            for mid in ALL_MODELS:
                adv = m["probs"][mid]["advHome"]
                assert abs(adv - b["reach"][mid][m["homeTeam"]]["r16"]) < 2e-5

    n_cand = sum(1 for m in b["matches"] if m["candidates"])
    n_played = sum(1 for m in b["matches"] if m["status"] == "played")
    print(f"Export checks OK: 12 groups (24 direct + 8 thirds), 32 bracket matches "
          f"({n_played} played, {n_cand} with candidates), reach {len(ALL_MODELS)} "
          f"models x 32 teams, params + resolution recorded")


def main() -> None:
    played, _ = load_and_prepare()
    ratings, _counts, _last, _n = run()
    groups = load_groups()
    spec = load_bracket_spec()
    rows = wc2026_rows(played)
    group_rows, ko_rows = split_group_knockout(rows, spec)
    tables = group_tables(groups, group_rows)
    validate_inputs(groups, spec, tables, group_rows, ratings)
    resolved = resolve_bracket(spec, ko_rows, load_shootout_winners())
    validate_played_conventions(resolved)

    print("Fitting all four models on every played match (takes a minute)...")
    samples = build_samples()
    fits = fit_all(samples)
    projs = project_all(resolved, ratings, fits)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    groups_json = build_groups_json(tables, generated)
    bracket_json = build_bracket_json(resolved, projs, ratings, fits, generated)

    DATA.mkdir(parents=True, exist_ok=True)
    gp, bp = DATA / "groups.json", DATA / "bracket.json"
    gp.write_text(json.dumps(groups_json, indent=2), encoding="utf-8")
    bp.write_text(json.dumps(bracket_json, indent=2), encoding="utf-8")
    print(f"Wrote {gp}  ({gp.stat().st_size / 1024:.0f} KB)")
    print(f"Wrote {bp}  ({bp.stat().st_size / 1024:.0f} KB)")
    _verify_exports(gp, bp)


if __name__ == "__main__":
    main()
