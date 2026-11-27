"""Stage 1 - fetch the latest HQ image of each radar and keep every new one.

TMD overwrites <code>240_HQ_latest.jpg every cycle and keeps no history, so anything
not fetched is lost. This module only downloads, checks and stores; the scan time is
read from the image footer later (stage 2), because the server sends no Last-Modified
header (checked 27 Nov 2026).

File name: data/raw/<CODE>/<YYYY>/<MM>/<DD>/<CODE>_<YYYYmmddTHHMMSS>Z_<sha8>.jpg
           (time = fetch time, UTC)
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image

from ..config import Radar

INV_FIELDS = ["fetch_utc", "code", "status", "sha256", "bytes", "width", "height",
              "http_status", "attempts", "path", "error"]


@dataclass
class Result:
    fetch_utc: str
    code: str
    status: str               # new | duplicate | error
    sha256: str = ""
    bytes: int = 0
    width: int = 0
    height: int = 0
    http_status: int = 0
    attempts: int = 0
    path: str = ""
    error: str = ""


@dataclass
class Collector:
    root: Path
    user_agent: str
    timeout_s: float = 40
    retries: int = 3
    backoff_s: float = 10
    min_bytes: int = 50_000
    session: requests.Session = field(default_factory=requests.Session)
    sleep = staticmethod(time.sleep)

    # ---------------------------------------------------------------- state
    @property
    def state_file(self) -> Path:
        return self.root / "state" / "last_hash.json"

    def load_state(self) -> dict:
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_state(self, state: dict) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")

    # ---------------------------------------------------------------- fetch
    def _download(self, url: str) -> tuple[bytes, int]:
        r = self.session.get(url, headers={"User-Agent": self.user_agent,
                                           "Cache-Control": "no-cache"}, timeout=self.timeout_s)
        status = r.status_code
        r.raise_for_status()
        return r.content, status

    def _check_image(self, data: bytes) -> tuple[int, int]:
        if len(data) < self.min_bytes:
            raise ValueError(f"file too small ({len(data)} B)")
        img = Image.open(io.BytesIO(data))
        if img.format != "JPEG":
            raise ValueError(f"not a JPEG ({img.format})")
        img.load()                          # raises on truncated files
        return img.size

    def raw_path(self, code: str, t: datetime, sha: str) -> Path:
        return (self.root / "raw" / code / f"{t:%Y}" / f"{t:%m}" / f"{t:%d}"
                / f"{code}_{t:%Y%m%dT%H%M%S}Z_{sha[:8]}.jpg")

    def fetch_one(self, radar: Radar, state: dict) -> Result:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        res = Result(fetch_utc=now.isoformat().replace("+00:00", "Z"), code=radar.code, status="error")
        for attempt in range(1, self.retries + 1):
            res.attempts = attempt
            try:
                data, res.http_status = self._download(radar.url)
                res.width, res.height = self._check_image(data)
                break
            except Exception as e:                      # network, HTTP or image error
                res.error = f"{type(e).__name__}: {e}"[:300]
                if isinstance(e, requests.HTTPError) and e.response is not None:
                    res.http_status = e.response.status_code
                if attempt < self.retries:
                    self.sleep(self.backoff_s * attempt)
        else:
            return res
        res.error = ""
        res.sha256 = hashlib.sha256(data).hexdigest()
        res.bytes = len(data)
        if state.get(radar.code) == res.sha256:
            res.status = "duplicate"
            return res
        p = self.raw_path(radar.code, now, res.sha256)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        res.path = p.relative_to(self.root).as_posix()
        res.status = "new"
        state[radar.code] = res.sha256
        return res

    # ---------------------------------------------------------------- run
    def run(self, radars: list[Radar], repeat: int = 1, interval_s: float = 0) -> list[Result]:
        state = self.load_state()
        results: list[Result] = []
        for k in range(repeat):
            for r in radars:
                results.append(self.fetch_one(r, state))
            self.save_state(state)                       # keep progress if the job is cut
            if k < repeat - 1:
                self.sleep(interval_s)
        self.write_inventory(results)
        return results

    def write_inventory(self, results: list[Result]) -> Path | None:
        """One CSV per job: data/inventory/YYYY/MM/DD/run_<HHMMSS>Z.csv (no appends, no clashes)."""
        if not results:
            return None
        t = datetime.fromisoformat(results[0].fetch_utc.replace("Z", "+00:00"))
        p = self.root / "inventory" / f"{t:%Y}" / f"{t:%m}" / f"{t:%d}" / f"run_{t:%H%M%S}Z.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=INV_FIELDS)
            w.writeheader()
            for r in results:
                w.writerow(asdict(r))
        return p
