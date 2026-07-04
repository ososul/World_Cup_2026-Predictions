"""Tournament projection — verified inputs, tallies, match probabilities, exact DP.

The group stage is finished FACT: `wc2026_groups.json` (final standings order + which
thirds advanced) and `wc2026_bracket.json` (the fixed M73-M104 knockout tree with the
real R32 pairings) are hand-entered verified data. This module never derives standings
or applies tiebreakers — it only cross-checks the entered sources against each other
and against results.csv, failing loudly on any inconsistency.

What it computes:
- Group tallies (W/D/L/GF/GA/GD/Pts): arithmetic over the 72 played group rows,
  presented in the user's entered order.
- Knockout resolution: a spec match becomes `played` when a results.csv row matches it
  by team pair + date (a level score resolves via shootouts.csv, else loud failure).
  Winner-refs (W73) / loser-refs (L101) then flow teams down the tree.
- Per-match probabilities for any (home, away) pairing at a bracket slot, per outcome
  model, with the three-leg advance decomposition
      P(advance) = P(win 90') + P(level 90') * [P(win ET) + P(level ET) * P(win pens)]
  ET is a Poisson mini-match — the fitted independent-Poisson rates scaled x 1/3
  (the only model with a time-rate structure); pens = 0.5 in v1 (plan backlog #1).
- Exact DP over the knockout tree (per model + ensemble): every slot holds a
  distribution over teams; P(t wins M) = P(t in slot) * sum_o P(o opposite) * pAdv(t,o)
  — exact because a match's two feeder subtrees are disjoint, so the occupants are
  independent. Played matches are point masses (appending results conditions the
  whole projection). Ratings stay static within the projection (plan backlog #2).
  Outputs: reach matrix {team -> P(R16/QF/SF/Final/Champion)} and per-slot arrival
  (candidate) distributions.

Ratings are the engine's current run (end of group stage; appended knockout rows
update them automatically on re-run). Host advantage: +90 only when USA / Mexico /
Canada play inside their own country (`venueCountry`); every other pairing is neutral.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prelim_elo"))
sys.path.insert(0, str(ROOT / "prelim_pred"))

from prepare import load_and_prepare, Match, RESULTS       # noqa: E402
from rating import HOME_ADVANTAGE                          # noqa: E402
from models import (                                       # noqa: E402
    davidson_probs, ordlogit_probs, dixoncoles_probs,
    poisson_lambdas, _poisson_pmf, _dc_tau,
    fit_davidson, fit_ordlogit, fit_poisson, fit_dixoncoles,
)

GROUPS_FILE = ROOT / "wc2026_groups.json"
BRACKET_FILE = ROOT / "wc2026_bracket.json"
SHOOTOUTS_FILE = ROOT / "data_set_copy" / "shootouts.csv"

WC = "FIFA World Cup"
HOSTS = {"United States", "Mexico", "Canada"}
ET_SCALE = 1.0 / 3.0   # extra time = 30 of 90 minutes at the same scoring rate
PENS_HOME = 0.5        # v1: shootout is a coin flip (fitted ladder = plan backlog #1)
MAX_GOALS = 15
MODEL_IDS = ("davidson", "ordlogit", "dixoncoles")
ROUND_SIZES = {"R32": 16, "R16": 8, "QF": 4, "SF": 2, "3rd": 1, "Final": 1}

_GROUP_SLOT = re.compile(r"^([12])([A-L])$")
_THIRD_SLOT = re.compile(r"^3rd\[([A-L](?:/[A-L])+)\]$")
_REF_SLOT = re.compile(r"^([WL])(\d+)$")
_DATE = re.compile(r"^2026-\d\d-\d\d$")
# which match numbers a round's winner/loser refs may point at
_REF_RANGE = {"R16": range(73, 89), "QF": range(89, 97), "SF": range(97, 101),
              "3rd": range(101, 103), "Final": range(101, 103)}


# ---------------------------------------------------------------- inputs

def load_groups() -> dict[str, dict]:
    raw = json.loads(GROUPS_FILE.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def load_bracket_spec() -> list[dict]:
    return json.loads(BRACKET_FILE.read_text(encoding="utf-8"))["matches"]


def load_shootout_winners() -> dict[tuple[str, frozenset], str]:
    """(date, {teamA, teamB}) -> shootout winner, for every recorded shootout."""
    with SHOOTOUTS_FILE.open(newline="", encoding="utf-8") as f:
        return {(r["date"], frozenset((r["home_team"], r["away_team"]))): r["winner"]
                for r in csv.DictReader(f)}


def wc2026_rows(played: list[Match]) -> list[Match]:
    return [m for m in played if m.tournament == WC and m.date >= "2026"]


def split_group_knockout(rows: list[Match], spec: list[dict]):
    """(group_rows, knockout_rows) split at the first R32 date from the bracket spec."""
    r32_dates = [m["date"] for m in spec if m["round"] == "R32"]
    if not all(r32_dates):
        raise ValueError("every R32 match in wc2026_bracket.json needs a date")
    ko_start = min(r32_dates)
    return [m for m in rows if m.date < ko_start], [m for m in rows if m.date >= ko_start]


# ---------------------------------------------------------------- group tallies

def group_tables(groups: dict, group_rows: list[Match]) -> dict[str, dict]:
    """Per group: the user's entered order with COMPUTED tallies, plus its 6 rows.

    Arithmetic only — the order (i.e. the standings) is entered fact, never derived.
    Requires each group's 4 teams to form an exact 6-match clique in the group rows.
    """
    by_pair: dict[frozenset, list[Match]] = {}
    for m in group_rows:
        by_pair.setdefault(frozenset((m.home, m.away)), []).append(m)

    tables: dict[str, dict] = {}
    for gid, g in sorted(groups.items()):
        order = g["order"]
        stats = {t: {"w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0} for t in order}
        rows: list[Match] = []
        for i, a in enumerate(order):
            for b in order[i + 1:]:
                pair = by_pair.get(frozenset((a, b)), [])
                if len(pair) != 1:
                    raise ValueError(f"group {gid}: expected exactly 1 played match "
                                     f"{a} vs {b}, found {len(pair)}")
                rows.append(pair[0])
        rows.sort(key=lambda m: m.date)
        for m in rows:
            sh, sa = stats[m.home], stats[m.away]
            sh["gf"] += m.home_score; sh["ga"] += m.away_score
            sa["gf"] += m.away_score; sa["ga"] += m.home_score
            if m.home_score > m.away_score:
                sh["w"] += 1; sa["l"] += 1
            elif m.home_score < m.away_score:
                sh["l"] += 1; sa["w"] += 1
            else:
                sh["d"] += 1; sa["d"] += 1
        table = []
        for pos, t in enumerate(order, 1):
            s = stats[t]
            qual = ("direct" if pos <= 2
                    else "third" if pos == 3 and g["thirdAdvanced"] else None)
            table.append({"pos": pos, "team": t, **s, "gd": s["gf"] - s["ga"],
                          "pts": 3 * s["w"] + s["d"], "qualified": qual})
        tables[gid] = {"table": table, "matches": rows}
    return tables


# ---------------------------------------------------------------- validation

def _rank_key(row: dict) -> tuple:
    """FIFA's first three group tiebreakers: points, overall GD, overall GF."""
    return row["pts"], row["gd"], row["gf"]


def validate_inputs(groups: dict, spec: list[dict], tables: dict,
                    group_rows: list[Match], ratings: dict) -> None:
    """Cross-check the two hand-entered files against each other, results.csv and
    the ratings. Consistency checks only — nothing here derives a standing."""
    errors: list[str] = []

    # groups file structure
    if sorted(groups) != list("ABCDEFGHIJKL"):
        errors.append(f"groups file must have exactly groups A-L, got {sorted(groups)}")
    all_teams = [t for g in groups.values() for t in g["order"]]
    if len(all_teams) != 48 or len(set(all_teams)) != 48:
        errors.append("groups must contain 48 distinct teams (4 per group)")
    flags = [gid for gid, g in sorted(groups.items()) if g["thirdAdvanced"] is True]
    if any(not isinstance(g["thirdAdvanced"], bool) for g in groups.values()):
        errors.append("every thirdAdvanced must be true or false (found null)")
    elif len(flags) != 8:
        errors.append(f"exactly 8 groups must have thirdAdvanced=true, got {len(flags)}")

    # every team resolves to a rating
    missing = sorted(t for t in set(all_teams) if t not in ratings)
    if missing:
        errors.append(f"teams without a rating (name mismatch?): {missing}")

    # every group-stage row consumed by exactly one group clique
    n_clique = sum(len(t["matches"]) for t in tables.values())
    if n_clique != len(group_rows):
        errors.append(f"{len(group_rows) - n_clique} group-stage rows in results.csv "
                      "belong to no group's 6-match clique")

    # entered order can never invert points, then GD, then GF (FIFA's first
    # three tiebreakers) — an inversion is a data-entry error, not a judgment call
    for gid, t in sorted(tables.items()):
        keys = [_rank_key(r) for r in t["table"]]
        for i in range(3):
            if keys[i + 1] > keys[i]:
                errors.append(f"group {gid}: entered order puts "
                              f"{t['table'][i + 1]['team']} {keys[i + 1]} below "
                              f"{t['table'][i]['team']} {keys[i]} "
                              "(pts/GD/GF inversion)")

    # an advanced third can never rank strictly below a non-advanced one
    if len(flags) == 8:
        thirds = {gid: tables[gid]["table"][2] for gid in groups}
        for u in (gid for gid in groups if gid not in flags):
            for f in flags:
                if _rank_key(thirds[u]) > _rank_key(thirds[f]):
                    errors.append(f"third-place flags: {thirds[u]['team']} ({u}, not "
                                  f"advanced) outranks {thirds[f]['team']} ({f}, "
                                  "advanced) on pts/GD/GF")

    # bracket skeleton
    nums = [m["match"] for m in spec]
    if nums != list(range(73, 105)):
        errors.append("bracket must hold exactly matches 73..104 in order")
    for rnd, size in ROUND_SIZES.items():
        got = sum(1 for m in spec if m["round"] == rnd)
        if got != size:
            errors.append(f"round {rnd}: expected {size} matches, got {got}")

    # R32 entries: teams filled, slot-consistent with the entered standings
    entered: list[str] = []
    for m in spec:
        if m["round"] != "R32":
            continue
        no = f"M{m['match']}"
        if not m["home"] or not m["away"]:
            errors.append(f"{no}: home/away must be filled")
            continue
        if not _DATE.match(m["date"] or ""):
            errors.append(f"{no}: date must be YYYY-MM-DD, got {m['date']!r}")
        if m["venueCountry"] not in HOSTS:
            errors.append(f"{no}: venueCountry must be one of {sorted(HOSTS)}")
        for slot, team in ((m["homeSlot"], m["home"]), (m["awaySlot"], m["away"])):
            entered.append(team)
            gm = _GROUP_SLOT.match(slot)
            tm = _THIRD_SLOT.match(slot)
            if gm:
                pos, gid = int(gm.group(1)), gm.group(2)
                want = groups[gid]["order"][pos - 1]
                if team != want:
                    errors.append(f"{no}: slot {slot} is {want} per groups file, "
                                  f"but {team} entered")
            elif tm:
                allowed = tm.group(1).split("/")
                ok = any(groups[g]["order"][2] == team and g in flags for g in allowed)
                if not ok:
                    errors.append(f"{no}: {team} is not an advanced third from "
                                  f"groups {allowed}")
            else:
                errors.append(f"{no}: unrecognised R32 slot {slot!r}")

    qualified = ({g["order"][0] for g in groups.values()}
                 | {g["order"][1] for g in groups.values()}
                 | {groups[gid]["order"][2] for gid in flags})
    if len(entered) == 32:
        if len(set(entered)) != 32:
            errors.append("R32 teams are not 32 distinct teams")
        elif set(entered) != qualified:
            errors.append(f"R32 teams != qualified set; missing "
                          f"{sorted(qualified - set(entered))}, extra "
                          f"{sorted(set(entered) - qualified)}")

    # later rounds: teams stay null, refs form the fixed tree
    ref_use: dict[str, int] = {}
    for m in spec:
        if m["round"] == "R32":
            continue
        no = f"M{m['match']}"
        if m["home"] or m["away"]:
            errors.append(f"{no}: home/away must stay null (resolved from play)")
        if not _DATE.match(m["date"] or ""):
            errors.append(f"{no}: date must be YYYY-MM-DD, got {m['date']!r}")
        if m["venueCountry"] not in HOSTS:
            errors.append(f"{no}: venueCountry must be one of {sorted(HOSTS)} "
                          "(the DP fixes host advantage per venue at every match)")
        for slot in (m["homeSlot"], m["awaySlot"]):
            rm = _REF_SLOT.match(slot)
            if not rm:
                errors.append(f"{no}: unrecognised ref slot {slot!r}")
                continue
            kind, target = rm.group(1), int(rm.group(2))
            if kind == "L" and m["match"] != 103:
                errors.append(f"{no}: loser-refs belong only in M103")
            if target not in _REF_RANGE[m["round"]]:
                errors.append(f"{no}: ref {slot} outside this round's feeder range")
            ref_use[slot] = ref_use.get(slot, 0) + 1
    expected_refs = {f"W{n}": 1 for n in range(73, 103)} | {"L101": 1, "L102": 1}
    if ref_use != expected_refs:
        diff = {k: v for k, v in (ref_use.items() | expected_refs.items())
                if ref_use.get(k) != expected_refs.get(k)}
        errors.append(f"bracket refs must use W73..W102 + L101/L102 exactly once "
                      f"each; mismatches: {sorted(diff)}")

    if errors:
        raise ValueError("input validation failed:\n  - " + "\n  - ".join(errors))


# ---------------------------------------------------------------- knockout resolution

def resolve_bracket(spec: list[dict], ko_rows: list[Match],
                    shootout_winners: dict) -> dict[int, dict]:
    """Flow real results through the tree -> {match_no: resolved match dict}.

    A spec match is `played` when a knockout row matches it by unordered team pair +
    date; scores are re-oriented to the spec's home/away designation. A level score
    needs a shootouts.csv winner. Every knockout row must join a spec match.
    """
    row_ix = {(m.date, frozenset((m.home, m.away))): m for m in ko_rows}
    if len(row_ix) != len(ko_rows):
        raise ValueError("duplicate knockout rows in results.csv (same teams + date)")

    by_no: dict[int, dict] = {}
    used: set = set()
    for m in sorted(spec, key=lambda m: m["match"]):
        r = dict(m)
        if m["round"] == "R32":
            r["homeTeam"], r["awayTeam"] = m["home"], m["away"]
        else:
            r["homeTeam"] = _slot_team(by_no, m["homeSlot"])
            r["awayTeam"] = _slot_team(by_no, m["awaySlot"])
        r.update(status="scheduled", result=None, winner=None, loser=None)
        if r["homeTeam"] and r["awayTeam"] and m["date"]:
            key = (m["date"], frozenset((r["homeTeam"], r["awayTeam"])))
            row = row_ix.get(key)
            if row is not None:
                used.add(key)
                flip = row.home != r["homeTeam"]
                hs = row.away_score if flip else row.home_score
                as_ = row.home_score if flip else row.away_score
                if hs == as_:
                    winner = shootout_winners.get(key)
                    if winner is None:
                        raise ValueError(
                            f"M{m['match']} {r['homeTeam']} v {r['awayTeam']} is level "
                            f"{hs}-{as_} but shootouts.csv names no winner")
                    if winner not in (r["homeTeam"], r["awayTeam"]):
                        raise ValueError(f"M{m['match']}: shootout winner {winner!r} "
                                         "is neither team")
                    pens = True
                else:
                    pens = False
                    winner = r["homeTeam"] if hs > as_ else r["awayTeam"]
                r["result"] = {"homeScore": hs, "awayScore": as_,
                               "winner": winner, "pens": pens}
                r["status"] = "played"
                r["winner"] = winner
                r["loser"] = r["awayTeam"] if winner == r["homeTeam"] else r["homeTeam"]
        by_no[m["match"]] = r

    leftovers = sorted(k for k in row_ix if k not in used)
    if leftovers:
        raise ValueError("knockout rows in results.csv matching no bracket entry "
                         f"(check team pair + date vs wc2026_bracket.json): {leftovers}")
    return by_no


def _slot_team(by_no: dict[int, dict], slot: str) -> str | None:
    rm = _REF_SLOT.match(slot)
    if not rm:
        return None
    target = by_no[int(rm.group(2))]
    return target["winner"] if rm.group(1) == "W" else target["loser"]


def validate_played_conventions(resolved: dict[int, dict]) -> None:
    """Check each played knockout row's CSV conventions against the bracket spec.

    The Elo engine gives home_team the +90 bump whenever neutral=FALSE, so a host
    playing at home MUST be the CSV row's home_team — else ratings silently corrupt.
    Also cross-checks the row's country column against the entered venueCountry.
    """
    raw: dict[tuple, dict] = {}
    with RESULTS.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["tournament"] == WC and row["date"] >= "2026":
                raw[(row["date"], frozenset((row["home_team"], row["away_team"])))] = row

    errors: list[str] = []
    for no, m in sorted(resolved.items()):
        if m["status"] != "played":
            continue
        row = raw[(m["date"], frozenset((m["homeTeam"], m["awayTeam"])))]
        venue = m["venueCountry"]
        if row["country"] != venue:
            errors.append(f"M{no}: results.csv country={row['country']!r} but "
                          f"bracket venueCountry={venue!r}")
        host = (m["homeTeam"] if m["homeTeam"] in HOSTS and venue == m["homeTeam"]
                else m["awayTeam"] if m["awayTeam"] in HOSTS and venue == m["awayTeam"]
                else None)
        if host is None:
            if row["neutral"] != "TRUE":
                errors.append(f"M{no}: no side is a host at home -> neutral must be TRUE")
        elif row["neutral"] != "FALSE" or row["home_team"] != host:
            errors.append(f"M{no}: {host} plays at home -> the CSV row must list "
                          f"{host} as home_team with neutral=FALSE (the engine gives "
                          f"home_team the +{HOME_ADVANTAGE})")
    if errors:
        raise ValueError("knockout CSV conventions violated:\n  - "
                         + "\n  - ".join(errors))


# ---------------------------------------------------------------- probabilities

def fit_all(samples) -> dict[str, dict]:
    """Fit all four models' free parameters on the given samples (production fit)."""
    nu = fit_davidson(samples)
    b, theta = fit_ordlogit(samples)
    mu_dc, beta_dc, rho = fit_dixoncoles(samples)
    mu_p, beta_p = fit_poisson(samples)
    return {"davidson": {"nu": nu},
            "ordlogit": {"b": b, "theta": theta},
            "dixoncoles": {"mu": mu_dc, "beta": beta_dc, "rho": rho},
            "poisson": {"mu": mu_p, "beta": beta_p}}


def h_eff(home: str, away: str, venue: str) -> int:
    """Host bump: only USA/Mexico/Canada inside their own country; else neutral."""
    if home in HOSTS and venue == home:
        return HOME_ADVANTAGE
    if away in HOSTS and venue == away:
        return -HOME_ADVANTAGE
    return 0


def probs90(dr: float, fits: dict) -> dict[str, tuple]:
    """90-minute (W, D, L) per model, plus their plain mean as `ensemble`."""
    p = {"davidson": davidson_probs(dr, fits["davidson"]["nu"]),
         "ordlogit": ordlogit_probs(dr, fits["ordlogit"]["b"], fits["ordlogit"]["theta"]),
         "dixoncoles": dixoncoles_probs(dr, **fits["dixoncoles"])}
    p["ensemble"] = tuple(sum(p[mid][i] for mid in MODEL_IDS) / len(MODEL_IDS)
                          for i in range(3))
    return p


def et_probs(dr: float, fits: dict) -> tuple[float, float, float]:
    """(W, D, L) of the 30-minute extra-time mini-match: Poisson rates x 1/3.

    Shared by all models — only the goals model has a per-minute rate structure,
    and Poisson memorylessness makes the 30' forecast exactly lambda/3.
    """
    lam_h, lam_a = poisson_lambdas(dr, fits["poisson"]["mu"], fits["poisson"]["beta"])
    ph = _poisson_pmf(lam_h * ET_SCALE, MAX_GOALS)
    pa = _poisson_pmf(lam_a * ET_SCALE, MAX_GOALS)
    w = d = lose = 0.0
    for i, pi in enumerate(ph):
        for j, pj in enumerate(pa):
            if i > j:
                w += pi * pj
            elif i == j:
                d += pi * pj
            else:
                lose += pi * pj
    total = w + d + lose
    return w / total, d / total, lose / total


def advance_from(p90: tuple, et: tuple) -> float:
    """Three-leg advance probability for the designated home side."""
    return p90[0] + p90[1] * (et[0] + et[1] * PENS_HOME)


def match_quote(home: str, away: str, venue: str, ratings: dict, fits: dict) -> dict:
    """Per model: 90' probs + the shared ET leg + pens + advance, for one pairing."""
    dr = ratings[home] - ratings[away] + h_eff(home, away, venue)
    p90 = probs90(dr, fits)
    et = et_probs(dr, fits)
    return {mid: {"p90": p90[mid], "et": et, "pensWin": PENS_HOME,
                  "advHome": advance_from(p90[mid], et)}
            for mid in (*MODEL_IDS, "ensemble")}


def dc_scorelines(home: str, away: str, venue: str, ratings: dict, fits: dict,
                  top: int = 3) -> list[tuple[str, float]]:
    """Most likely 90' scorelines under Dixon-Coles, as [('1-0', p), ...]."""
    dr = ratings[home] - ratings[away] + h_eff(home, away, venue)
    dc = fits["dixoncoles"]
    lam_h, lam_a = poisson_lambdas(dr, dc["mu"], dc["beta"])
    ph = _poisson_pmf(lam_h, MAX_GOALS)
    pa = _poisson_pmf(lam_a, MAX_GOALS)
    cells: list[tuple[str, float]] = []
    total = 0.0
    for i, pi in enumerate(ph):
        for j, pj in enumerate(pa):
            pij = pi * pj
            if i <= 1 and j <= 1:
                pij *= _dc_tau(i, j, lam_h, lam_a, dc["rho"])
                if pij < 0.0:
                    pij = 0.0
            cells.append((f"{i}-{j}", pij))
            total += pij
    cells.sort(key=lambda c: c[1], reverse=True)
    return [(s, p / total) for s, p in cells[:top]]


# ---------------------------------------------------------------- exact DP

_REACH_KEY = {"R32": "r16", "R16": "qf", "QF": "sf", "SF": "final", "Final": "champion"}


def adv_quotes(ratings: dict, fits: dict):
    """(home, away, venue) -> {model: P(home side advances)}, memoised.

    One cache serves all four DP runs: `match_quote` prices every model for a
    pairing in a single call, and hypothetical pairings recur across models.
    """
    cache: dict[tuple, dict[str, float]] = {}

    def q(home: str, away: str, venue: str) -> dict[str, float]:
        key = (home, away, venue)
        if key not in cache:
            mq = match_quote(home, away, venue, ratings, fits)
            cache[key] = {mid: mq[mid]["advHome"] for mid in mq}
        return cache[key]

    return q


def _slot_dist(m: dict, side: str, winner: dict, loser: dict) -> dict[str, float]:
    """Distribution over the teams that can occupy one slot of a match."""
    team = m[side + "Team"]
    if team:
        return {team: 1.0}
    rm = _REF_SLOT.match(m[side + "Slot"])
    if not rm:
        raise ValueError(f"M{m['match']}: cannot resolve {side} slot "
                         f"{m[side + 'Slot']!r}")
    src = winner if rm.group(1) == "W" else loser
    return src[int(rm.group(2))]


def project(resolved: dict[int, dict], adv) -> dict:
    """Exact DP over the knockout tree for one model.

    `adv(home, away, venue)` prices P(the designated home side advances) for any
    hypothetical pairing. Slots carry distributions over teams; a played match is
    a point mass on its real winner/loser, so appended results condition the whole
    projection. Exact because a match's feeder subtrees are disjoint: the two
    occupants are independent, and refs always point at lower match numbers, so
    one pass in match order suffices.

    Returns {"slots": {no: {"home"/"away": {team: p}}}, "winner": {no: {team: p}},
             "loser": {no: {team: p}}, "reach": {team: {r16/qf/sf/final/champion: p}}}.
    """
    slots: dict[int, dict] = {}
    winner: dict[int, dict[str, float]] = {}
    loser: dict[int, dict[str, float]] = {}
    for no, m in sorted(resolved.items()):
        hd = _slot_dist(m, "home", winner, loser)
        ad = _slot_dist(m, "away", winner, loser)
        if set(hd) & set(ad):
            raise ValueError(f"M{no}: {sorted(set(hd) & set(ad))} feed both slots "
                             "(bracket tree broken)")
        slots[no] = {"home": hd, "away": ad}
        if m["status"] == "played":
            winner[no] = {m["winner"]: 1.0}
            loser[no] = {m["loser"]: 1.0}
            continue
        venue = m["venueCountry"]
        w = {t: pt * sum(po * adv(t, o, venue) for o, po in ad.items())
             for t, pt in hd.items()}
        w |= {o: po * sum(pt * (1.0 - adv(t, o, venue)) for t, pt in hd.items())
              for o, po in ad.items()}
        winner[no] = w
        loser[no] = {t: hd.get(t, 0.0) + ad.get(t, 0.0) - p for t, p in w.items()}

    reach: dict[str, dict[str, float]] = {}
    for no, s in slots.items():
        for side in ("home", "away"):
            for t in s[side]:
                reach.setdefault(t, dict.fromkeys(_REACH_KEY.values(), 0.0))
    for no, m in sorted(resolved.items()):
        key = _REACH_KEY.get(m["round"])   # the 3rd-place match is not a reach stage
        if key:
            for t, p in winner[no].items():
                reach[t][key] += p
    return {"slots": slots, "winner": winner, "loser": loser, "reach": reach}


def project_all(resolved: dict[int, dict], ratings: dict, fits: dict) -> dict[str, dict]:
    """The exact DP per model (three models + ensemble) over one shared quote cache."""
    q = adv_quotes(ratings, fits)
    return {mid: project(resolved, lambda h, a, v, m=mid: q(h, a, v)[m])
            for mid in (*MODEL_IDS, "ensemble")}


# ---------------------------------------------------------------- verification

def _verify() -> None:
    from engine import run
    from dataset import build_samples

    print("=== Tournament projection - Steps 1-2: inputs, tallies, match probabilities ===")
    played, _ = load_and_prepare()
    ratings, _counts, _last, _n = run()
    groups = load_groups()
    spec = load_bracket_spec()
    rows = wc2026_rows(played)
    group_rows, ko_rows = split_group_knockout(rows, spec)
    print(f"WC-2026 rows: {len(rows)} "
          f"({len(group_rows)} group stage, {len(ko_rows)} knockout)")

    tables = group_tables(groups, group_rows)
    validate_inputs(groups, spec, tables, group_rows, ratings)
    print("Input validation: groups x bracket x results.csv x ratings consistent  OK")

    # tally arithmetic invariants (every group)
    for gid, t in tables.items():
        tab = t["table"]
        assert all(r["w"] + r["d"] + r["l"] == 3 for r in tab), gid
        assert sum(r["gf"] for r in tab) == sum(r["ga"] for r in tab), gid
        assert sum(r["w"] for r in tab) == sum(r["l"] for r in tab), gid
        assert all(r["pts"] == 3 * r["w"] + r["d"] for r in tab), gid
    print("Tally invariants (3 games each, GF=GA, W=L, pts arithmetic): all 12 groups OK")

    print("\nGroup A (entered order, computed tallies) - eyeball vs the real table:")
    for r in tables["A"]["table"]:
        q = {"direct": "->R32", "third": "->R32 (3rd)", None: ""}[r["qualified"]]
        print(f"  {r['pos']}. {r['team']:<16} {r['w']}-{r['d']}-{r['l']}  "
              f"{r['gf']}:{r['ga']} ({r['gd']:+d})  {r['pts']} pts {q}")

    # knockout resolution on the real data
    resolved = resolve_bracket(spec, ko_rows, load_shootout_winners())
    validate_played_conventions(resolved)
    n_played = sum(m["status"] == "played" for m in resolved.values())
    assert n_played == len(ko_rows)
    assert all(resolved[n]["homeTeam"] and resolved[n]["awayTeam"]
               for n in range(73, 89))
    print(f"\nKnockout resolution: {n_played}/32 played, R32 slots all filled  OK")

    # resolution unit tests with injected fake rows (the CSV is never touched)
    fake = [Match("2026-06-28", "Canada", "South Africa", True, WC, 60, 2, 1),
            Match("2026-07-02", "Portugal", "Croatia", True, WC, 60, 1, 1)]
    fake_so = {("2026-07-02", frozenset(("Portugal", "Croatia"))): "Croatia"}
    rt = resolve_bracket(spec, fake, fake_so)
    assert rt[73]["status"] == "played" and rt[73]["winner"] == "Canada"
    assert (rt[73]["result"]["homeScore"], rt[73]["result"]["awayScore"]) == (1, 2), \
        "scores must re-orient to the spec's home/away"
    assert rt[83]["winner"] == "Croatia" and rt[83]["result"]["pens"] is True
    assert rt[90]["homeTeam"] == "Canada" and rt[93]["homeTeam"] == "Croatia", \
        "winners must flow into the R16 slots"
    try:
        resolve_bracket(spec, fake, {})
        raise AssertionError("level match without a shootout winner must fail")
    except ValueError as e:
        assert "shootouts.csv" in str(e)
    try:
        resolve_bracket(spec, [Match("2026-06-28", "Brazil", "Norway", True, WC, 60, 1, 0)], {})
        raise AssertionError("unjoinable knockout row must fail")
    except ValueError as e:
        assert "no bracket entry" in str(e)
    print("Resolution unit tests (injected fakes, incl. loud failures): OK")

    # model fits (production fit: all played matches)
    print("\nFitting all four models on every played match (takes a minute)...")
    samples = build_samples()
    fits = fit_all(samples)
    print(f"  {len(samples):,} matches")
    print(f"  davidson   nu={fits['davidson']['nu']:.5f}")
    print(f"  ordlogit   b={fits['ordlogit']['b']:.6f} theta={fits['ordlogit']['theta']:.5f}")
    dc = fits["dixoncoles"]
    print(f"  dixoncoles mu={dc['mu']:.5f} beta={dc['beta']:.5f} rho={dc['rho']:+.5f}")
    po = fits["poisson"]
    print(f"  poisson    mu={po['mu']:.5f} beta={po['beta']:.5f}  (ET leg)")

    # probability identities across a dr sweep
    for dr in (-400.0, -250.0, -90.0, 0.0, 90.0, 250.0, 400.0):
        p90, p90m = probs90(dr, fits), probs90(-dr, fits)
        et, etm = et_probs(dr, fits), et_probs(-dr, fits)
        for mid in (*MODEL_IDS, "ensemble"):
            # mirror symmetry: flipping dr flips home/away exactly
            assert all(abs(p90[mid][i] - p90m[mid][2 - i]) < 1e-12 for i in range(3))
            # the two advance probabilities sum to 1 exactly
            a_home = advance_from(p90[mid], et)
            a_away = advance_from(p90m[mid], etm)
            assert abs(a_home + a_away - 1.0) < 1e-12, (dr, mid)
        assert all(abs(et[i] - etm[2 - i]) < 1e-12 for i in range(3))
        # ensemble linearity: advance(mean p90) == mean(advance) exactly
        a_ens = advance_from(p90["ensemble"], et)
        a_mean = sum(advance_from(p90[mid], et) for mid in MODEL_IDS) / len(MODEL_IDS)
        assert abs(a_ens - a_mean) < 1e-12
    p90_0, et_0 = probs90(0.0, fits), et_probs(0.0, fits)
    for mid in (*MODEL_IDS, "ensemble"):
        assert abs(p90_0[mid][0] - p90_0[mid][2]) < 1e-12
        assert abs(advance_from(p90_0[mid], et_0) - 0.5) < 1e-12
    assert abs(et_0[0] - et_0[2]) < 1e-12
    # ET grid truncation loses nothing at the extremes of the plausible dr range
    lam_h, lam_a = poisson_lambdas(400.0, po["mu"], po["beta"])
    raw = sum(_poisson_pmf(lam_h * ET_SCALE, MAX_GOALS)) \
        * sum(_poisson_pmf(lam_a * ET_SCALE, MAX_GOALS))
    assert raw > 1.0 - 1e-9
    print("Probability identities (mirror, adv sums to 1, dr=0 -> 0.5, ensemble "
          "linearity, ET truncation): OK")

    # R32 spot table (ensemble 90' + per-model advance) for user eyeballing
    print("\nR32 - ensemble 90' W/D/L and P(advance, home side) per model:")
    print(f"  {'':4}{'pairing':<34}{'ven':<5}{'dr':>5}  {'90 W/D/L %':<17}"
          f"{'dav':>6}{'ord':>6}{'dc':>6}{'ens':>6}")
    venue_code = {"United States": "USA", "Mexico": "MEX", "Canada": "CAN"}
    for no in range(73, 89):
        m = resolved[no]
        home, away, venue = m["homeTeam"], m["awayTeam"], m["venueCountry"]
        dr = ratings[home] - ratings[away] + h_eff(home, away, venue)
        q = match_quote(home, away, venue, ratings, fits)
        w, d, lo = (100 * p for p in q["ensemble"]["p90"])
        advs = "".join(f"{100 * q[mid]['advHome']:6.1f}"
                       for mid in (*MODEL_IDS, "ensemble"))
        star = "*" if h_eff(home, away, venue) else " "
        print(f"  M{no} {home + ' v ' + away:<34}{venue_code[venue]:<4}{star}"
              f"{dr:>5.0f}  {w:4.1f}/{d:4.1f}/{lo:4.1f}  {advs}")

    ex = dc_scorelines("Argentina", "Cape Verde", "United States", ratings, fits)
    print("\nDC top scorelines, M86 Argentina v Cape Verde: "
          + ", ".join(f"{s} ({100 * p:.1f}%)" for s, p in ex))

    # ---- Step 3: exact DP ----
    print("\n=== Step 3: exact DP - reach matrix, candidates, ensemble ===")

    # the 4-team toy bracket from the design discussion, hand-computed reference:
    # SF1 A v B, SF2 C v D, winners meet; fixed advance table, venue-free
    tbl = {("A", "B"): 0.70, ("C", "D"): 0.60, ("A", "C"): 0.65,
           ("A", "D"): 0.80, ("B", "C"): 0.45, ("B", "D"): 0.60}

    def toy_adv(h, a, v):
        return tbl[(h, a)] if (h, a) in tbl else 1.0 - tbl[(a, h)]

    def toy_match(no, rnd, home=None, away=None, hs="", as_=""):
        return {"match": no, "round": rnd, "venueCountry": "", "status": "scheduled",
                "homeTeam": home, "awayTeam": away, "homeSlot": hs, "awaySlot": as_,
                "winner": None, "loser": None}

    toy = {1: toy_match(1, "SF", "A", "B"), 2: toy_match(2, "SF", "C", "D"),
           3: toy_match(3, "Final", hs="W1", as_="W2")}
    tp = project(toy, toy_adv)
    want = {"A": 0.497, "B": 0.153, "C": 0.246, "D": 0.104}
    assert all(abs(tp["winner"][3][t] - p) < 1e-12 for t, p in want.items())
    assert abs(sum(tp["winner"][3].values()) - 1.0) < 1e-12
    assert abs(sum(tp["reach"][t]["final"] for t in "ABCD") - 2.0) < 1e-12
    print("Toy 4-team bracket reproduces hand-computed 0.497/0.153/0.246/0.104: OK")

    print("Running the exact DP (3 models + ensemble)...")
    projs = project_all(resolved, ratings, fits)

    # DP invariants, every model: distributions sum to 1, reach columns sum to
    # the round sizes, reach is monotone down the rounds, all 32 teams present
    field = {"r16": 16.0, "qf": 8.0, "sf": 4.0, "final": 2.0, "champion": 1.0}
    for mid, pr in projs.items():
        for no in resolved:
            for side in ("home", "away"):
                assert abs(sum(pr["slots"][no][side].values()) - 1.0) < 1e-9, (mid, no)
            assert abs(sum(pr["winner"][no].values()) - 1.0) < 1e-9, (mid, no)
        assert len(pr["reach"]) == 32, mid
        for key, tot in field.items():
            got = sum(r[key] for r in pr["reach"].values())
            assert abs(got - tot) < 1e-9, (mid, key, got)
        for t, r in pr["reach"].items():
            seq = [r["r16"], r["qf"], r["sf"], r["final"], r["champion"]]
            assert all(seq[i] >= seq[i + 1] - 1e-12 for i in range(4)), (mid, t)
    print("DP invariants (dists sum to 1, reach columns = 16/8/4/2/1, monotone, "
          "32 teams) x 4 models: OK")

    # 3rd-place slots must equal the SF-loser identity P(in SF) - P(in Final)
    for mid, pr in projs.items():
        for side in ("home", "away"):
            for t, p in pr["slots"][103][side].items():
                r = pr["reach"][t]
                assert abs(p - (r["sf"] - r["final"])) < 1e-12, (mid, t)
    print("3rd-place slots = P(reach SF) - P(reach Final), team by team: OK")

    # ensemble linearity holds through one DP level (R32 slots are point masses)
    for no in range(73, 89):
        for t, p in projs["ensemble"]["winner"][no].items():
            mean = sum(projs[mid]["winner"][no][t] for mid in MODEL_IDS) / len(MODEL_IDS)
            assert abs(p - mean) < 1e-12, (no, t)
    print("Ensemble R32 winner dists = mean of the three models (linearity): OK")

    # played matches condition the DP: inject the step-2 fakes and re-project
    pf = project_all(resolve_bracket(spec, fake, fake_so), ratings, fits)["ensemble"]
    assert pf["winner"][73] == {"Canada": 1.0}
    assert pf["reach"]["Canada"]["r16"] == 1.0
    assert pf["reach"]["South Africa"] == dict.fromkeys(field, 0.0)
    assert pf["slots"][90]["home"] == {"Canada": 1.0}
    assert pf["winner"][83] == {"Croatia": 1.0}
    assert pf["slots"][93]["home"] == {"Croatia": 1.0}
    assert abs(sum(r["champion"] for r in pf["reach"].values()) - 1.0) < 1e-9
    print("Resolved-match propagation (fake results -> point masses downstream): OK")

    # reach matrix for user eyeballing: top 12 by ensemble champion probability
    ens = projs["ensemble"]["reach"]
    top = sorted(ens, key=lambda t: -ens[t]["champion"])[:12]
    print("\nReach matrix (ensemble, %) - top 12 by champion | champion per model:")
    print(f"  {'team':<16}{'R16':>6}{'QF':>6}{'SF':>6}{'Final':>6}{'Champ':>7}"
          f"  |{'dav':>6}{'ord':>6}{'dc':>6}")
    for t in top:
        r = ens[t]
        by_model = "".join(f"{100 * projs[mid]['reach'][t]['champion']:6.1f}"
                           for mid in MODEL_IDS)
        print(f"  {t:<16}{100 * r['r16']:6.1f}{100 * r['qf']:6.1f}{100 * r['sf']:6.1f}"
              f"{100 * r['final']:6.1f}{100 * r['champion']:7.1f}  |{by_model}")

    # candidate (arrival) distributions: the favourite's possible R16 opponents
    fav = top[0]
    slot_of = {(no, side): projs["ensemble"]["slots"][no][side]
               for no in range(89, 97) for side in ("home", "away")}
    no, side = next(k for k, d in slot_of.items() if fav in d)
    opp = slot_of[(no, "away" if side == "home" else "home")]
    cands = sorted(opp.items(), key=lambda kv: -kv[1])
    print(f"\n{fav} R16 (M{no}) opponent distribution: "
          + ", ".join(f"{t} {100 * p:.1f}%" for t, p in cands))
    print("Final (M104) slot candidates (ensemble, top 5 a side):")
    for side in ("home", "away"):
        cands = sorted(projs["ensemble"]["slots"][104][side].items(),
                       key=lambda kv: -kv[1])[:5]
        print(f"  {side:<5} " + ", ".join(f"{t} {100 * p:.1f}%" for t, p in cands))

    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    _verify()
