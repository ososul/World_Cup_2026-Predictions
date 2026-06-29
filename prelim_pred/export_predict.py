"""Export fitted prediction-model parameters for the frontend (predict.json).

Fits each outcome model's free parameters on ALL played matches — the production
fit (the temporal hold-out is only for validation, see checkin1.py) — and writes
the small registry the frontend's match-odds panel reads. Adding a model later =
fit it and append an entry here, plus a matching function in the frontend's MODELS.

    python3 prelim_pred/export_predict.py   # -> web/public/data/predict.json
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
from models import fit_davidson, fit_ordlogit, fit_dixoncoles   # noqa: E402

DATA = ROOT / "web" / "public" / "data"


def main() -> None:
    samples = build_samples()
    nu = fit_davidson(samples)
    b, theta = fit_ordlogit(samples)
    mu, beta, rho = fit_dixoncoles(samples)
    registry = {
        "eloScale": 400,
        "homeAdvantage": HOME_ADVANTAGE,
        "ratingSystem": "prelim_elo",
        "models": [
            {"id": "davidson", "label": "Davidson (Preliminary Elo)",
             "params": {"nu": round(nu, 5)}},
            {"id": "ordlogit", "label": "Ordered logistic (Preliminary Elo)",
             "params": {"b": round(b, 6), "theta": round(theta, 5)}},
            {"id": "dixoncoles", "label": "Dixon-Coles (Preliminary Elo)",
             "params": {"mu": round(mu, 5), "beta": round(beta, 5), "rho": round(rho, 5)}},
        ],
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "predict.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print(f"Wrote {DATA / 'predict.json'}  ({len(samples):,} matches; "
          f"davidson nu={nu:.5f}; ordlogit b={b:.6f} theta={theta:.5f}; "
          f"dixoncoles mu={mu:.5f} beta={beta:.5f} rho={rho:+.5f})")


if __name__ == "__main__":
    main()
