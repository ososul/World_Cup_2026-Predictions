"""Export fitted prediction-model parameters for the frontend (predict.json).

Fits each outcome model's free parameters on ALL played matches — the production
fit (the temporal hold-out is only for validation, see checkin1.py) — and writes
the small registry the frontend's match-odds panel reads. Adding a model later =
fit it and append an entry here, plus a matching function in the frontend's MODELS.

    python3 prelim_pred/export_predict.py   # -> frontend/data/predict.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prelim_elo"))
sys.path.insert(0, str(ROOT / "prelim_pred"))

from rating import HOME_ADVANTAGE       # noqa: E402
from dataset import build_samples        # noqa: E402
from models import fit_davidson          # noqa: E402

DATA = ROOT / "frontend" / "data"


def main() -> None:
    samples = build_samples()
    nu = fit_davidson(samples)
    registry = {
        "eloScale": 400,
        "homeAdvantage": HOME_ADVANTAGE,
        "ratingSystem": "prelim_elo",
        "models": [
            {"id": "davidson", "label": "Davidson (Preliminary Elo)",
             "params": {"nu": round(nu, 5)}},
        ],
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "predict.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print(f"Wrote {DATA / 'predict.json'}  ({len(samples):,} matches; davidson nu={nu:.5f})")


if __name__ == "__main__":
    main()
