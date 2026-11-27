"""Load YAML settings from config/ (repo root is found from this file or $CPMOSAIC_ROOT)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(os.environ.get("CPMOSAIC_ROOT", Path(__file__).resolve().parents[2]))
CONFIG = ROOT / "config"


def load_yaml(name: str) -> dict:
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass(frozen=True)
class Radar:
    code: str
    name: str
    lat: float
    lon: float
    pos_err_km: float
    layout: str
    product: str
    url: str


def radars(codes: list[str] | None = None) -> list[Radar]:
    cfg = load_yaml("radars.yaml")
    out = []
    for r in cfg["radars"]:
        if codes and r["code"] not in codes:
            continue
        url = cfg["url_template"].format(code_lower=r["code"].lower(), code=r["code"])
        out.append(Radar(url=url, **r))
    return out
