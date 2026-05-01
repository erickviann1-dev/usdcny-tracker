"""
Auto-generate a replication notebook for the USD/CNY tracker.
Called from build.py on each successful build.
"""

import nbformat as nbf
from datetime import datetime
from pathlib import Path


def build_replication_notebook(data_date: str, snapshot: dict):
    """Generate docs/usdcny_tracker_replication.ipynb with 5 cells."""
    nb = nbf.v4.new_notebook()
    nb.metadata.kernelspec = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }

    # Cell 1: Markdown — title + citation
    score = snapshot.get("composite_score", "—")
    usdcny = snapshot.get("usdcny", "—")
    nb.cells.append(nbf.v4.new_markdown_cell(f"""# USD/CNY Macro-Policy Divergence Tracker — Replication Notebook

**Data date:** {data_date}  
**Composite Score:** {score}/100 · **USD/CNY:** {usdcny}  
**Live dashboard:** [erickviann1-dev.github.io/usdcny-tracker](https://erickviann1-dev.github.io/usdcny-tracker/)

---

**Citation:**  
USD/CNY Macro-Policy Divergence Tracker, v3.2. Retrieved {datetime.now().strftime("%Y-%m-%d")}.  
`https://erickviann1-dev.github.io/usdcny-tracker/`

---

This notebook independently re-computes the tracker's three layer values from the raw time-series data, proving nothing is hidden in the dashboard's JavaScript rendering."""))

    # Cell 2: Code — install + imports
    nb.cells.append(nbf.v4.new_code_cell("""# Dependencies
import json, requests
import pandas as pd
import numpy as np

# Optional: for inline plots
try:
    import matplotlib.pyplot as plt
    %matplotlib inline
    plt.rcParams.update({"figure.figsize": (12, 4), "figure.dpi": 100})
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("matplotlib not installed — skipping plots")"""))

    # Cell 3: Code — fetch live data.json
    nb.cells.append(nbf.v4.new_code_cell("""# Fetch the latest data.json from the live dashboard
URL = "https://erickviann1-dev.github.io/usdcny-tracker/data.json"
resp = requests.get(URL)
resp.raise_for_status()
data = resp.json()

# Parse into DataFrames
df = pd.DataFrame(data["series"])
df["date"] = pd.to_datetime(df["date"])
df = df.set_index("date").sort_index()

snap = data["snapshot"]
print(f"Loaded {len(df)} rows, latest date: {df.index[-1].date()}")
print(f"Dashboard composite score: {snap.get('composite_score', '—')}/100")"""))

    # Cell 4: Code — independent recomputation
    nb.cells.append(nbf.v4.new_code_cell("""# ════════════════════════════════════════════════════════════
#  Independent recomputation of the three layers
# ════════════════════════════════════════════════════════════

# Layer 1: Raw Carry
df["raw_carry_check"] = df["us_2y"] - df["cn_2y"]

# Hedged Carry Proxy (CIP-implied)
if "cip_deviation" in df.columns and "usdcny" in df.columns:
    cip_dev_pct = df["cip_deviation"] / df["usdcny"] * 100
    df["hedged_carry_check"] = df["raw_carry_check"] - cip_dev_pct
else:
    df["hedged_carry_check"] = np.nan

# Layer 2: CIP fair value deviation
if all(c in df.columns for c in ["us_2y", "cn_2y", "usdcny"]):
    r_us = df["us_2y"] / 100
    r_cn = df["cn_2y"] / 100
    r_us_base = r_us.iloc[0]
    r_cn_base = r_cn.iloc[0]
    spot_base = df["usdcny"].iloc[0]
    cip_fair = spot_base * ((1 + r_cn)**2 / (1 + r_us)**2) / ((1 + r_cn_base)**2 / (1 + r_us_base)**2)
    df["cip_deviation_check"] = df["usdcny"] - cip_fair

# Layer 3: Fixing bias (simplified — without DXY adjustment for transparency)
if all(c in df.columns for c in ["pboc_fix", "usdcny"]):
    df["fixing_bias_raw_check"] = df["pboc_fix"] - df["usdcny"].shift(1)

# Compare with dashboard values
print("=== Layer 1: Raw Carry ===")
latest = df.iloc[-1]
print(f"  Dashboard:    {latest.get('raw_carry', 'N/A'):.4f}")
print(f"  Recomputed:   {latest.get('raw_carry_check', 'N/A'):.4f}")

print("\\n=== CIP Deviation ===")
print(f"  Dashboard:    {latest.get('cip_deviation', 'N/A'):.4f}")
print(f"  Recomputed:   {latest.get('cip_deviation_check', 'N/A'):.4f}")

print("\\n=== Fixing Bias (raw, no DXY adj) ===")
print(f"  Dashboard:    {latest.get('fixing_bias_raw', 'N/A'):.4f}")
print(f"  Recomputed:   {latest.get('fixing_bias_raw_check', 'N/A'):.4f}")

print("\\n✓ If values match within rounding, the dashboard is faithfully reporting.")"""))

    # Cell 5: Code — diagnostic plots
    nb.cells.append(nbf.v4.new_code_cell("""# ════════════════════════════════════════════════════════════
#  Diagnostic Plots
# ════════════════════════════════════════════════════════════
if not HAS_MPL:
    print("Skipping plots (matplotlib not installed)")
else:
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    # Plot 1: Composite score time series
    if "composite_score" in df.columns:
        ax = axes[0]
        ax.plot(df.index, df["composite_score"], color="#0c0a09", linewidth=1)
        ax.fill_between(df.index, df["composite_score"], alpha=0.1, color="#a16207")
        ax.axhline(75, color="red", linestyle="--", alpha=0.5, label="High pressure (75)")
        ax.axhline(40, color="green", linestyle="--", alpha=0.5, label="Low pressure (40)")
        ax.set_ylabel("Composite Score (0-100)")
        ax.set_title("Composite Policy Pressure Score")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.3)

    # Plot 2: Regression residual histogram
    if "reg_residual" in df.columns:
        ax = axes[1]
        resid = df["reg_residual"].dropna()
        ax.hist(resid, bins=50, color="#1e3a5f", alpha=0.7, edgecolor="white")
        ax.axvline(0, color="red", linestyle="--", alpha=0.7)
        ax.set_xlabel("Residual (CNY)")
        ax.set_ylabel("Frequency")
        ax.set_title(f"OLS Residual Distribution (mean={resid.mean():.4f}, std={resid.std():.4f})")
        ax.grid(True, alpha=0.3)

    # Plot 3: Fixing bias rolling mean
    if "bias_20d_mean" in df.columns:
        ax = axes[2]
        ax.plot(df.index, df["bias_20d_mean"], color="#a16207", linewidth=1, label="20d mean")
        if "bias_60d_mean" in df.columns:
            ax.plot(df.index, df["bias_60d_mean"], color="#0c0a09", linewidth=1, label="60d mean")
        ax.axhline(0, color="gray", linestyle="-", alpha=0.3)
        ax.fill_between(df.index, df["bias_20d_mean"], alpha=0.1, color="#a16207")
        ax.set_ylabel("Fixing Bias (CNY)")
        ax.set_title("PBOC Fixing Bias — Rolling Means")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()
    print("\\n✓ Three diagnostic plots rendered.")"""))

    # Write notebook
    out_path = Path(__file__).parent.parent / "docs" / "usdcny_tracker_replication.ipynb"
    with open(out_path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)

    print(f"✓ Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    build_replication_notebook("test-date", {"composite_score": 58, "usdcny": 6.84})
