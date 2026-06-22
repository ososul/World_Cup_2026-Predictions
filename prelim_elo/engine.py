"""Preliminary Elo System (spec: PreliminaryEloSystem.md) - Step 4: chronological run.

Replays every played match in date order, carrying running ratings (new teams
start at 1500) and per-team match counts, to produce the current rating table.
"""
from __future__ import annotations

from prepare import load_and_prepare
from rating import match_deltas

INITIAL = 1500
PROVISIONAL_MATCHES = 30  # ratings below this many games are flagged provisional


def run(record_history: bool = False):
    """Replay all played matches -> (ratings, counts, last_date, n_processed).

    With record_history=True, also returns a fifth value {team: [(date, rating), ...]}
    holding each team's rating after every match it played (for the time series).
    """
    played, _ = load_and_prepare()
    ratings: dict[str, int] = {}
    counts: dict[str, int] = {}
    last_date: dict[str, str] = {}
    history: dict[str, list[tuple[str, int]]] = {}
    for m in played:
        rh = ratings.get(m.home, INITIAL)
        ra = ratings.get(m.away, INITIAL)
        dh, da = match_deltas(rh, ra, m.neutral, m.k_eff, m.home_score, m.away_score)
        ratings[m.home] = rh + dh
        ratings[m.away] = ra + da
        for t in (m.home, m.away):
            counts[t] = counts.get(t, 0) + 1
            last_date[t] = m.date
            if record_history:
                history.setdefault(t, []).append((m.date, ratings[t]))
    if record_history:
        return ratings, counts, last_date, len(played), history
    return ratings, counts, last_date, len(played)


def _verify() -> None:
    print("=== Step 4: chronological run ===")
    played, _ = load_and_prepare()
    ratings, counts, last_date, n = run()

    # accounting: every played match consumed, two team-appearances each
    assert n == len(played)
    assert sum(counts.values()) == 2 * n
    print(f"Matches processed:    {n}  (latest {max(last_date.values())})")
    print(f"Teams rated:          {len(ratings)}")

    # hand-check the very first match (both teams start at INITIAL)
    f = played[0]
    dh, da = match_deltas(INITIAL, INITIAL, f.neutral, f.k_eff, f.home_score, f.away_score)
    print(f"First match {f.date}: {f.home} {f.home_score}-{f.away_score} {f.away} "
          f"(neutral={f.neutral}, k_eff={f.k_eff}) -> {f.home} {dh:+d}, {f.away} {da:+d}")

    # global point conservation: zero-sum updates => sum stays at INITIAL * teams
    drift = sum(ratings.values()) - INITIAL * len(ratings)
    print(f"Point conservation:   sum(ratings) - {INITIAL}*teams = {drift:+d}")

    # plausibility peek (full table + WC-48 view come in Step 5)
    print("\nTop 20 (peek):")
    top = sorted(ratings.items(), key=lambda kv: kv[1], reverse=True)[:20]
    for rank, (team, r) in enumerate(top, 1):
        prov = "*" if counts[team] < PROVISIONAL_MATCHES else " "
        print(f"  {rank:>2}. {team:<24} {r:>5} {prov} ({counts[team]} games)")


if __name__ == "__main__":
    _verify()
