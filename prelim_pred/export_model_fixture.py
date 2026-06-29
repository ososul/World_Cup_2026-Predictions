"""Emit a reference fixture pinning the frontend's TS model port to this Python source.

For each outcome model, evaluates the Python probability function at a spread of rating
differences using the SAME fitted params the frontend reads from predict.json, and writes
the (dr -> [P_home, P_draw, P_away]) triples. web/__tests__/models.test.ts then asserts the
TS port (web/lib/models.ts) reproduces these numbers, so the two implementations cannot
drift apart silently.

    python3 prelim_pred/export_model_fixture.py   # -> web/__tests__/fixtures/model_probs.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prelim_elo"))
sys.path.insert(0, str(ROOT / "prelim_pred"))

from models import davidson_probs, ordlogit_probs, dixoncoles_probs  # noqa: E402

# Within +/-800 the Dixon-Coles tau stays positive (no clamp), so Python and the TS port
# must agree to floating-point precision across this whole range.
DRS = [-800, -500, -300, -150, -50, 0, 50, 150, 300, 500, 800]

PREDICT = ROOT / "web" / "public" / "data" / "predict.json"
OUT = ROOT / "web" / "__tests__" / "fixtures" / "model_probs.json"

FUNCS = {
    "davidson": davidson_probs,
    "ordlogit": ordlogit_probs,
    "dixoncoles": dixoncoles_probs,
}


def main() -> None:
    params = {m["id"]: m["params"] for m in json.loads(PREDICT.read_text())["models"]}
    fixture = {
        mid: {
            "params": params[mid],
            "cases": [{"dr": dr, "probs": list(FUNCS[mid](dr, **params[mid]))} for dr in DRS],
        }
        for mid in FUNCS
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fixture, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}  ({len(DRS)} dr values x {len(FUNCS)} models)")


if __name__ == "__main__":
    main()
