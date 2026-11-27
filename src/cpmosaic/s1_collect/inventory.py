"""Read the per-job inventory CSVs back into one table and summarise completeness.

    from cpmosaic.s1_collect.inventory import load, daily_summary
    inv = load("data")                    # all runs found under data/inventory
    daily_summary(inv)                    # new images per radar per day (96 expected)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load(root: str | Path) -> pd.DataFrame:
    files = sorted(Path(root, "inventory").rglob("run_*.csv"))
    if not files:
        return pd.DataFrame()
    inv = pd.concat((pd.read_csv(f, dtype={"error": str, "path": str}) for f in files), ignore_index=True)
    inv["fetch_utc"] = pd.to_datetime(inv["fetch_utc"], utc=True)
    return inv


def daily_summary(inv: pd.DataFrame, expected_per_day: int = 96) -> pd.DataFrame:
    if inv.empty:
        return inv
    d = inv[inv["status"] == "new"].assign(day=lambda x: x["fetch_utc"].dt.strftime("%Y-%m-%d"))
    t = d.groupby(["day", "code"])["sha256"].nunique().unstack(fill_value=0)
    t.columns.name = None
    t["expected"] = expected_per_day
    return t


def trial_report(inv: pd.DataFrame, slot_min: int = 15) -> pd.DataFrame:
    """One row per radar for the trial check: did every station's images reach the archive, how often,
    with what gaps. A new image every ~15 min and no long gaps means the station is collected fully.

    columns: requests, new, duplicate, error, error_rate, first_utc, last_utc, hours,
             new_per_day (96 = complete), median_step_min, max_gap_min, median_mb, sizes (W x H seen)
    """
    if inv.empty:
        return inv
    rows = []
    for code, g in inv.groupby("code", sort=False):
        new = g[g["status"] == "new"].sort_values("fetch_utc")
        t0, t1 = g["fetch_utc"].min(), g["fetch_utc"].max()
        hours = max((t1 - t0).total_seconds() / 3600, slot_min / 60)
        steps = new["fetch_utc"].diff().dt.total_seconds().div(60).dropna()
        sizes = sorted({f"{int(w)}x{int(h)}" for w, h in zip(new["width"], new["height"])})
        rows.append({
            "code": code,
            "requests": len(g),
            "new": len(new),
            "duplicate": int((g["status"] == "duplicate").sum()),
            "error": int((g["status"] == "error").sum()),
            "error_rate": round(float((g["status"] == "error").mean()), 3),
            "first_utc": t0, "last_utc": t1, "hours": round(hours, 1),
            "new_per_day": round(len(new) / hours * 24, 1),
            "median_step_min": round(float(steps.median()), 1) if len(steps) else None,
            "max_gap_min": round(float(steps.max()), 1) if len(steps) else None,
            "median_mb": round(float(new["bytes"].median()) / 1e6, 2) if len(new) else None,
            "sizes": ", ".join(sizes),
        })
    return pd.DataFrame(rows).set_index("code")
