"""
Yield prediction model (scikit-learn HistGradientBoostingRegressor).

Training data: an agronomic simulation built from published crop-response
relationships (FAO-33 water-yield response Ky, Mitscherlich nutrient response,
temperature optima, disease-severity loss). This gives a model that responds
correctly to every input on the dashboard.

To train on real field records instead, see training/train_yield.py --csv.
"""
from __future__ import annotations

import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.core.crops import CROPS, STAGE_DISEASE_WEIGHT, STAGE_HEAT_WEIGHT, STAGE_WATER_WEIGHT

MODELS = Path(__file__).resolve().parents[2] / "models"
MODEL_PATH = MODELS / "yield_model.joblib"
CROP_KEYS = list(CROPS)
FEATURES = ["crop", "stage", "n", "p", "k", "ph", "temp_mean", "water_ratio",
            "heat_days", "disease_severity", "disease_aggr", "prev_legume"]


def _suff(x, opt, floor):
    """Mitscherlich-type sufficiency curve: floor at x=0, ~1 at x>=opt."""
    v = (1 - np.exp(-2.5 * np.asarray(x) / opt)) / (1 - math.exp(-2.5))
    return np.clip(floor + (1 - floor) * v, floor, 1.0)


def _range_penalty(x, lo, hi, width):
    x = np.asarray(x, dtype=float)
    dist = np.where(x < lo, lo - x, np.where(x > hi, x - hi, 0.0))
    return np.exp(-(dist / width) ** 2)


def factors(df: pd.DataFrame) -> pd.DataFrame:
    """Each limiting factor as a 0-1 multiplier (used for simulation + explanations)."""
    out = pd.DataFrame(index=df.index)
    meta = df["crop"].map(CROPS)
    st = df["stage"].astype(int)
    n_eff = df["n"] + 40 * df["prev_legume"]
    out["nitrogen"] = _suff(n_eff, meta.map(lambda m: m["n_need"]), 0.45)
    out["phosphorus"] = _suff(df["p"], meta.map(lambda m: m["p_need"]), 0.60)
    out["potassium"] = _suff(df["k"], meta.map(lambda m: m["k_need"]), 0.65)
    out["soil_ph"] = np.clip(_range_penalty(df["ph"], meta.map(lambda m: m["ph_opt"][0]),
                                            meta.map(lambda m: m["ph_opt"][1]), 1.3), 0.4, 1)
    out["temperature"] = np.clip(_range_penalty(df["temp_mean"], meta.map(lambda m: m["t_opt"][0]),
                                                meta.map(lambda m: m["t_opt"][1]), 7.0), 0.35, 1)
    ky = meta.map(lambda m: m["ky"])
    ww = st.map(lambda i: STAGE_WATER_WEIGHT[i])
    out["water"] = np.clip(1 - ky * (1 - df["water_ratio"]) * ww, 0.1, 1)
    hw = st.map(lambda i: STAGE_HEAT_WEIGHT[i])
    out["heat"] = np.clip(1 - 0.035 * df["heat_days"] * hw, 0.5, 1)
    dw = st.map(lambda i: STAGE_DISEASE_WEIGHT[i])
    out["disease"] = np.clip(1 - 1.2 * df["disease_severity"] * df["disease_aggr"] * dw, 0.05, 1)
    return out


def simulate(n_rows: int = 40000, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(dict(
        crop=rng.choice(CROP_KEYS, n_rows),
        stage=rng.integers(0, 4, n_rows),
        n=rng.uniform(80, 650, n_rows),
        p=rng.uniform(4, 60, n_rows),
        k=rng.uniform(60, 450, n_rows),
        ph=rng.uniform(4.5, 9.0, n_rows),
        temp_mean=rng.uniform(10, 38, n_rows),
        water_ratio=np.clip(rng.beta(5, 1.6, n_rows), 0.05, 1),
        heat_days=rng.integers(0, 8, n_rows),
        disease_severity=np.where(rng.random(n_rows) < 0.45, 0, rng.beta(1.5, 4, n_rows)),
        disease_aggr=rng.choice([0.35, 0.45, 0.55, 0.7, 0.9, 1.0], n_rows),
        prev_legume=rng.integers(0, 2, n_rows),
    ))
    f = factors(df)
    rel = f.prod(axis=1) * rng.lognormal(0, 0.06, n_rows)
    df["yield_t_ha"] = df["crop"].map(lambda c: CROPS[c]["base_yield"]) * rel
    return df


def _encode(df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURES].copy()
    X["crop"] = X["crop"].map({c: i for i, c in enumerate(CROP_KEYS)}).astype(int)
    return X


def train(df: pd.DataFrame | None = None, save: bool = True) -> dict:
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import train_test_split

    df = simulate() if df is None else df
    X, y = _encode(df), df["yield_t_ha"] / df["crop"].map(lambda c: CROPS[c]["base_yield"])
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=0)
    model = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.08, max_leaf_nodes=48,
                                          categorical_features=[0], random_state=0)
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    sub = Xte.sample(min(3000, len(Xte)), random_state=0)
    imp = permutation_importance(model, sub, yte.loc[sub.index], n_repeats=4, random_state=0)
    importance = sorted(zip(FEATURES, imp.importances_mean.round(4).tolist()), key=lambda t: -t[1])
    metrics = dict(r2=round(float(r2_score(yte, pred)), 4), mae_rel=round(float(mean_absolute_error(yte, pred)), 4),
                   n_train=len(Xtr), n_test=len(Xte), importance=importance,
                   algorithm="HistGradientBoostingRegressor")
    bundle = dict(model=model, metrics=metrics, features=FEATURES, crops=CROP_KEYS)
    if save:
        MODELS.mkdir(exist_ok=True)
        joblib.dump(bundle, MODEL_PATH)
    return bundle


_bundle = None


def load() -> dict:
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else train()
    return _bundle


def predict(rows: list[dict]) -> np.ndarray:
    """Returns predicted yield in t/ha for each feature dict."""
    b = load()
    df = pd.DataFrame(rows)
    rel = b["model"].predict(_encode(df))
    base = df["crop"].map(lambda c: CROPS[c]["base_yield"]).to_numpy()
    return np.clip(rel, 0.02, 1.15) * base
