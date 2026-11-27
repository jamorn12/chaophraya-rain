"""Status bundle for the admin page: rolling history, latest image per radar, thumbnails.

The GitHub runner starts empty every 15 min, so the rolling history and the thumbnails live in
data/state/ (copied to and from the archive remote with last_hash.json). This module

1. merges the inventory CSVs of this job into data/state/history.csv (kept for `keep_days`),
2. refreshes data/state/thumbs/<CODE>.jpg from every new image of this job,
3. writes the public bundle  <site>/data/status/{latest.json, history_48h.csv, thumbs/<CODE>.jpg}
   that the admin page reads from GitHub Pages.

    python -m cpmosaic.s1_collect.status --root data --site site
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from PIL import Image

from .. import control
from ..config import ROOT, load_yaml, radars
from . import inventory

HIST_COLS = ["fetch_utc", "code", "status", "bytes", "width", "height", "http_status", "error", "path"]


def update_history(root: Path, keep_days: float = 7, now: datetime | None = None) -> pd.DataFrame:
    root = Path(root)
    p = root / "state" / "history.csv"
    parts = []
    if p.exists():
        parts.append(pd.read_csv(p, dtype={"error": str, "path": str}))
    inv = inventory.load(root)
    if not inv.empty:
        parts.append(inv)
    if not parts:
        h = pd.DataFrame(columns=HIST_COLS)
        h["fetch_utc"] = pd.to_datetime(h["fetch_utc"], utc=True)
        return h
    h = pd.concat(parts, ignore_index=True)
    h["fetch_utc"] = pd.to_datetime(h["fetch_utc"], utc=True)
    h = h.reindex(columns=HIST_COLS)
    h = h.drop_duplicates(["fetch_utc", "code"], keep="last").sort_values("fetch_utc")
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    h = h[h["fetch_utc"] >= now - pd.Timedelta(days=keep_days)].reset_index(drop=True)
    p.parent.mkdir(parents=True, exist_ok=True)
    out = h.copy()
    out["fetch_utc"] = out["fetch_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.to_csv(p, index=False)
    return h


def refresh_thumbs(root: Path, hist: pd.DataFrame, size: int = 900) -> list[str]:
    """Make state/thumbs/<CODE>.jpg from the newest image of each radar that is on disk now."""
    root = Path(root)
    tdir = root / "state" / "thumbs"
    tdir.mkdir(parents=True, exist_ok=True)
    done = []
    new = hist[hist["status"] == "new"].dropna(subset=["path"])
    for code, g in new.groupby("code"):
        src = root / str(g.iloc[-1]["path"])
        if not src.exists():
            continue                      # older image from an earlier job: keep the thumb we have
        im = Image.open(src).convert("RGB")
        im.thumbnail((size, size), Image.LANCZOS)
        im.save(tdir / f"{code}.jpg", "JPEG", quality=82, optimize=True)
        meta = {"fetch_utc": str(g.iloc[-1]["fetch_utc"]), "path": str(g.iloc[-1]["path"])}
        (tdir / f"{code}.json").write_text(json.dumps(meta))
        done.append(code)
    return done


def summary(hist: pd.DataFrame, now: datetime | None = None, stale_min: float = 45) -> dict:
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    day = hist[hist["fetch_utc"] >= now - pd.Timedelta(hours=24)]
    out = []
    for r in radars():
        g = hist[hist["code"] == r.code]
        new = g[g["status"] == "new"]
        last_new = new["fetch_utc"].max() if len(new) else None
        last_try = g["fetch_utc"].max() if len(g) else None
        d = day[day["code"] == r.code]
        last = new.iloc[-1] if len(new) else None
        age = None if last_new is None else (now - last_new).total_seconds() / 60
        out.append({
            "code": r.code, "name": r.name, "lat": r.lat, "lon": r.lon, "layout": r.layout, "product": r.product,
            "last_new_utc": None if last_new is None else last_new.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_try_utc": None if last_try is None else last_try.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "age_min": None if age is None else round(age, 1),
            "fresh": age is not None and age <= stale_min,
            "new_24h": int((d["status"] == "new").sum()),
            "dup_24h": int((d["status"] == "duplicate").sum()),
            "err_24h": int((d["status"] == "error").sum()),
            "last_error": "" if not len(g[g["status"] == "error"]) else str(g[g["status"] == "error"].iloc[-1]["error"])[:200],
            "bytes": None if last is None else int(last["bytes"]),
            "size": None if last is None else f"{int(last['width'])}x{int(last['height'])}",
            "path": None if last is None else str(last["path"]),
        })
    return {"generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "stale_min": stale_min, "radars": out}


def build_site(root: Path, site: Path, hist: pd.DataFrame, now: datetime | None = None) -> Path:
    root, site = Path(root), Path(site)
    d = site / "data" / "status"
    (d / "thumbs").mkdir(parents=True, exist_ok=True)
    s = summary(hist, now)
    s["control"] = control.status_payload(control.load())
    cfg = load_yaml("collect.yaml")
    s["archive"] = {"label": cfg.get("archive_label", ""), "url": cfg.get("archive_url", "")}
    (d / "latest.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    h48 = hist[hist["fetch_utc"] >= now - pd.Timedelta(hours=48)].copy()
    h48["fetch_utc"] = h48["fetch_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    h48.drop(columns=["path"]).to_csv(d / "history_48h.csv", index=False)
    for f in (root / "state" / "thumbs").glob("*"):
        shutil.copy2(f, d / "thumbs" / f.name)
    return d


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cpmosaic.s1_collect.status")
    ap.add_argument("--root", type=Path, default=ROOT / "data")
    ap.add_argument("--site", type=Path, default=ROOT / "site")
    ap.add_argument("--keep-days", type=float, default=7)
    a = ap.parse_args(argv)
    hist = update_history(a.root, a.keep_days)
    th = refresh_thumbs(a.root, hist)
    d = build_site(a.root, a.site, hist)
    print(f"history {len(hist)} rows · thumbs refreshed {','.join(th) or '-'} · bundle {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
