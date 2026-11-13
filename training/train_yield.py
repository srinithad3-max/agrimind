"""
Train / re-train the yield model and print its evaluation.

  python training/train_yield.py                 # agronomic simulation (default)
  python training/train_yield.py --csv my.csv    # your own field records

A custom CSV must contain these columns:
  crop (tomato|potato|maize|rice|wheat|cotton|chilli|groundnut), stage (0-3),
  n, p, k (kg/ha), ph, temp_mean (°C), water_ratio (0-1), heat_days,
  disease_severity (0-1), disease_aggr (0-1), prev_legume (0/1), yield_t_ha
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from app.ml import yield_model  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--csv")
a = ap.parse_args()

df = pd.read_csv(a.csv) if a.csv else None
b = yield_model.train(df)
m = b["metrics"]
print(f"Algorithm : {m['algorithm']}")
print(f"Train/test: {m['n_train']} / {m['n_test']}")
print(f"R²        : {m['r2']}")
print(f"MAE       : {m['mae_rel']:.3f} (fraction of benchmark yield)")
print("Permutation importance:")
for f, v in m["importance"]:
    print(f"  {f:18s} {v:.4f}")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names, vals = zip(*m["importance"][::-1])
    plt.figure(figsize=(6, 4))
    plt.barh(names, vals, color="#2F8F5B")
    plt.title(f"Yield model: feature importance (R² {m['r2']})")
    plt.tight_layout()
    out = Path(__file__).resolve().parents[1] / "models" / "yield_feature_importance.png"
    plt.savefig(out, dpi=150)
    print("saved", out)
except Exception as e:
    print("plot skipped:", e)
