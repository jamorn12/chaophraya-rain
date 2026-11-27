"""Command line: python -m cpmosaic.s1_collect [--repeat N] [--interval S] [--radars CRI,PHS] [--root data] [--force]

Does nothing when the system switch (config/control.yaml) is off, unless --force is given.

Exit code 0 even when some radars fail (failures are in the inventory); exit code 2 only
when every request of the job failed, so the workflow shows a red mark for a full outage.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .. import control
from ..config import ROOT, load_yaml, radars
from .fetch import Collector


def main(argv: list[str] | None = None) -> int:
    cfg = load_yaml("collect.yaml")
    ap = argparse.ArgumentParser(prog="cpmosaic.s1_collect")
    ap.add_argument("--repeat", type=int, default=cfg["repeat"])
    ap.add_argument("--interval", type=float, default=cfg["interval_s"])
    ap.add_argument("--radars", default="", help="comma list, default all nine")
    ap.add_argument("--root", type=Path, default=ROOT / cfg["data_root"])
    ap.add_argument("--force", action="store_true", help="collect even when the system switch is off")
    a = ap.parse_args(argv)

    if not a.force and not control.is_enabled():
        print("system is OFF (config/control.yaml): nothing collected; use --force to test")
        return 0

    col = Collector(root=a.root, user_agent=cfg["user_agent"], timeout_s=cfg["timeout_s"],
                    retries=cfg["retries"], backoff_s=cfg["backoff_s"], min_bytes=cfg["min_bytes"])
    rs = radars([c.strip().upper() for c in a.radars.split(",") if c.strip()] or None)
    results = col.run(rs, repeat=a.repeat, interval_s=a.interval)

    by = Counter((r.code, r.status) for r in results)
    for r in rs:
        print(f"{r.code}: new {by[(r.code, 'new')]}, duplicate {by[(r.code, 'duplicate')]}, "
              f"error {by[(r.code, 'error')]}")
    errors = [r for r in results if r.status == "error"]
    for e in errors:
        print(f"  ! {e.code} {e.fetch_utc} http={e.http_status} {e.error}", file=sys.stderr)
    return 2 if results and len(errors) == len(results) else 0


if __name__ == "__main__":
    sys.exit(main())
