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


BOX = (960, 800)          # every thumbnail is letterboxed into the same 6:5 box (most TMD images are 1920x1600)
FRAME_BOX = (640, 533)
BG = (14, 17, 22)
N_FRAMES = 8              # newest images kept per radar for the admin film strip (about 2 h)


def letterbox(src: Path, box: tuple[int, int]) -> Image.Image:
    im = Image.open(src).convert("RGB")
    im.thumbnail(box, Image.LANCZOS)
    out = Image.new("RGB", box, BG)
    out.paste(im, ((box[0] - im.width) // 2, (box[1] - im.height) // 2))
    return out


def refresh_thumbs(root: Path, hist: pd.DataFrame) -> list[str]:
    """state/thumbs/<CODE>.jpg from data/latest/<CODE>.jpg (the newest bytes of this job, new or duplicate);
    state/frames/<CODE>/<CODE>_<fetch>Z.jpg from every new image of this job, keeping the newest N_FRAMES."""
    root = Path(root)
    tdir, fdir = root / "state" / "thumbs", root / "state" / "frames"
    tdir.mkdir(parents=True, exist_ok=True)
    done = []
    for src in sorted((root / "latest").glob("*.jpg")):
        code = src.stem
        letterbox(src, BOX).save(tdir / f"{code}.jpg", "JPEG", quality=84, optimize=True)
        g = hist[hist["code"] == code]
        meta = {"fetch_utc": None if g.empty else g["fetch_utc"].max().strftime("%Y-%m-%dT%H:%M:%SZ")}
        (tdir / f"{code}.json").write_text(json.dumps(meta))
        done.append(code)
    new = hist[hist["status"] == "new"].dropna(subset=["path"])
    for code, g in new.groupby("code"):
        out = fdir / code
        out.mkdir(parents=True, exist_ok=True)
        for _, row in g.iterrows():
            src = root / str(row["path"])
            dst = out / f"{code}_{row['fetch_utc']:%Y%m%dT%H%M%S}Z.jpg"
            if src.exists() and not dst.exists():
                letterbox(src, FRAME_BOX).save(dst, "JPEG", quality=80, optimize=True)
    for out in fdir.glob("*"):
        for old in sorted(out.glob("*.jpg"))[:-N_FRAMES]:
            old.unlink()
    return done


def daily_counts(hist: pd.DataFrame, days: int = 7, now: datetime | None = None) -> list[dict]:
    """New images per radar per Thai day (UTC+7), last `days` days. 96 = complete."""
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    h = hist[(hist["status"] == "new") & (hist["fetch_utc"] >= now - pd.Timedelta(days=days))]
    if h.empty:
        return []
    day = h["fetch_utc"].dt.tz_convert("Asia/Bangkok").dt.strftime("%Y-%m-%d")
    t = h.assign(day=day).groupby(["day", "code"]).size().rename("n").reset_index()
    return t.to_dict("records")


def size_changes(hist: pd.DataFrame) -> dict:
    """Image sizes seen per radar in the history. More than one size = the TMD layout may have changed."""
    new = hist[(hist["status"] == "new") & (hist["width"] > 0)]
    out = {}
    for code, g in new.groupby("code"):
        sz = (g["width"].astype(int).astype(str) + "x" + g["height"].astype(int).astype(str))
        first = g.assign(sz=sz).groupby("sz")["fetch_utc"].min().sort_values()
        out[code] = [{"size": k, "first_utc": v.strftime("%Y-%m-%dT%H:%M:%SZ")} for k, v in first.items()]
    return out


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
    new7 = hist[hist["status"] == "new"]
    totals = {"bytes_24h": int(day.loc[day["status"] == "new", "bytes"].fillna(0).sum()),
              "bytes_7d": int(new7["bytes"].fillna(0).sum()),
              "images_7d": int(len(new7)),
              "requests_24h": int(len(day)),
              "errors_24h": int((day["status"] == "error").sum())}
    return {"generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "stale_min": stale_min, "radars": out,
            "totals": totals}


def build_site(root: Path, site: Path, hist: pd.DataFrame, now: datetime | None = None) -> Path:
    root, site = Path(root), Path(site)
    d = site / "data" / "status"
    (d / "thumbs").mkdir(parents=True, exist_ok=True)
    s = summary(hist, now)
    s["control"] = control.status_payload(control.load())
    cfg = load_yaml("collect.yaml")
    s["archive"] = {"label": cfg.get("archive_label", ""), "url": cfg.get("archive_url", "")}
    s["daily"] = daily_counts(hist, now=now)
    s["sizes"] = size_changes(hist)
    frames = {}
    for out in sorted((root / "state" / "frames").glob("*")):
        fs = sorted(out.glob("*.jpg"))
        if fs:
            (d / "frames" / out.name).mkdir(parents=True, exist_ok=True)
            for f in fs:
                shutil.copy2(f, d / "frames" / out.name / f.name)
            frames[out.name] = [f.name for f in fs]
    s["frames"] = frames
    (d / "latest.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    h48 = hist[hist["fetch_utc"] >= now - pd.Timedelta(hours=48)].copy()
    h48["fetch_utc"] = h48["fetch_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    h48.drop(columns=["path"]).to_csv(d / "history_48h.csv", index=False)
    for f in (root / "state" / "thumbs").glob("*"):
        if f.is_dir():
            continue
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
