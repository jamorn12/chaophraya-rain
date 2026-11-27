"""System on/off switch.

The switch lives in config/control.yaml (committed to the repo), so every workflow reads it right after
checkout and the change history is the git log. The public site reads web/public/data/status.json:
when the system is off it stops showing a live clock and loops the last forecast that was made.

    python -m cpmosaic.control status           # print the state
    python -m cpmosaic.control status --gha     # also write run=true/false to $GITHUB_OUTPUT
    python -m cpmosaic.control off --reason "dry season" --by jamorn12
    python -m cpmosaic.control on  --reason "trial collection"

Workflows started by hand with force=true run even when the switch is off (for tests).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .config import ROOT

CONTROL_FILE = Path("config") / "control.yaml"
STATUS_FILE = Path("web") / "public" / "data" / "status.json"

DEFAULT = {"enabled": True, "changed_utc": None, "changed_by": None, "reason": None}


def _utc(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(root: Path = ROOT) -> dict:
    p = Path(root) / CONTROL_FILE
    if not p.exists():
        return dict(DEFAULT)
    with open(p, encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    out = dict(DEFAULT)
    out.update(d)
    if not isinstance(out["enabled"], bool):
        raise ValueError(f"{p}: 'enabled' must be true or false, got {out['enabled']!r}")
    return out


def is_enabled(root: Path = ROOT) -> bool:
    return load(root)["enabled"]


def status_payload(state: dict) -> dict:
    """What the public and admin pages read. 'mode' tells the public page what to draw."""
    return {
        "enabled": state["enabled"],
        "mode": "live" if state["enabled"] else "paused_loop_last_forecast",
        "changed_utc": state["changed_utc"],
        "changed_by": state["changed_by"],
        "reason": state["reason"],
        "message_th": None if state["enabled"] else "ระบบพักการเก็บข้อมูลชั่วคราว ภาพที่แสดงคือพยากรณ์ชุดล่าสุดก่อนพัก",
        "message_en": None if state["enabled"] else "Data collection is paused. Showing the last forecast made before the pause.",
    }


def set_state(enabled: bool, reason: str = "", by: str = "", root: Path = ROOT,
              now: datetime | None = None) -> dict:
    state = {"enabled": bool(enabled), "changed_utc": _utc(now), "changed_by": by or None,
             "reason": reason or None}
    p = Path(root) / CONTROL_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    header = ("# System switch. Change it with the 'control' workflow (Actions > control > Run workflow)\n"
              "# or the admin page; do not edit by hand while workflows are running.\n")
    with open(p, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.safe_dump(state, f, sort_keys=False, allow_unicode=True)
    s = Path(root) / STATUS_FILE
    s.parent.mkdir(parents=True, exist_ok=True)
    s.write_text(json.dumps(status_payload(state), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return state


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cpmosaic.control")
    ap.add_argument("action", choices=["status", "on", "off"])
    ap.add_argument("--reason", default="")
    ap.add_argument("--by", default=os.environ.get("GITHUB_ACTOR", ""))
    ap.add_argument("--force", default="false", help="status only: 'true' makes run=true even when off")
    ap.add_argument("--gha", action="store_true", help="status only: write run=... to $GITHUB_OUTPUT")
    ap.add_argument("--root", type=Path, default=ROOT)
    a = ap.parse_args(argv)

    if a.action in ("on", "off"):
        st = set_state(a.action == "on", a.reason, a.by, a.root)
        print(f"system {'ON' if st['enabled'] else 'OFF'} at {st['changed_utc']} by {st['changed_by']}"
              f" ({st['reason'] or 'no reason given'})")
        return 0

    st = load(a.root)
    force = str(a.force).lower() == "true"
    run = st["enabled"] or force
    print(f"system {'ON' if st['enabled'] else 'OFF'}"
          f" (since {st['changed_utc'] or '-'}, by {st['changed_by'] or '-'}, reason: {st['reason'] or '-'})"
          + ("  -> forced run" if force and not st["enabled"] else ""))
    if a.gha:
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a") as f:
                f.write(f"run={'true' if run else 'false'}\n")
        if not run:
            print("::notice::System is OFF (config/control.yaml) - nothing collected this run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
