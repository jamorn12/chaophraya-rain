"""Offline tests for stage 1 (no network): a fake session serves JPEG bytes."""
import io

import pytest
import requests
from PIL import Image

from cpmosaic.config import radars
from cpmosaic.s1_collect import inventory
from cpmosaic.s1_collect.fetch import Collector


def jpeg(seed: int, size=(400, 300)) -> bytes:
    img = Image.effect_noise(size, 60 + seed).convert("RGB")
    b = io.BytesIO(); img.save(b, "JPEG", quality=95)
    return b.getvalue()


class FakeResp:
    def __init__(self, content=b"", status=200):
        self.content, self.status_code = content, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}", response=self)


class FakeSession:
    """Returns queued responses per URL; an Exception in the queue is raised."""
    def __init__(self, plan):
        self.plan, self.calls = plan, []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        item = self.plan[url].pop(0) if len(self.plan[url]) > 1 else self.plan[url][0]
        if isinstance(item, Exception):
            raise item
        return item


def make(tmp_path, plan):
    c = Collector(root=tmp_path, user_agent="test", retries=3, backoff_s=0, min_bytes=1000,
                  session=FakeSession(plan))
    c.sleep = lambda s: None
    return c


def test_nine_radars_and_urls():
    rs = radars()
    assert [r.code for r in rs] == ["CRI", "LMP", "TAK", "PHS", "PHB", "CHN", "KKW", "SVP", "SKM"]
    assert rs[3].url == "https://weather.tmd.go.th/phs/phs240_HQ_latest.jpg"


def test_new_then_duplicate_then_new(tmp_path):
    r = radars(["PHS"])[0]
    a, b = jpeg(1), jpeg(2)
    c = make(tmp_path, {r.url: [FakeResp(a), FakeResp(a), FakeResp(b)]})
    res = c.run([r], repeat=3)
    assert [x.status for x in res] == ["new", "duplicate", "new"]
    assert len(list((tmp_path / "raw" / "PHS").rglob("*.jpg"))) == 2
    assert c.load_state()["PHS"] == res[-1].sha256
    inv = inventory.load(tmp_path)
    assert len(inv) == 3 and set(inv.status) == {"new", "duplicate"}
    assert int(inventory.daily_summary(inv)["PHS"].iloc[0]) == 2


def test_retry_then_success(tmp_path):
    r = radars(["CRI"])[0]
    c = make(tmp_path, {r.url: [requests.ConnectionError("down"), FakeResp(status=503), FakeResp(jpeg(3))]})
    res = c.run([r])[0]
    assert res.status == "new" and res.attempts == 3 and res.error == ""


def test_broken_image_is_an_error(tmp_path):
    r = radars(["LMP"])[0]
    c = make(tmp_path, {r.url: [FakeResp(b"<html>not found</html>" * 100)]})
    res = c.run([r])[0]
    assert res.status == "error"
    assert "JPEG" in res.error or "identify" in res.error
    assert not (tmp_path / "raw").exists()


def test_state_survives_between_jobs(tmp_path):
    r = radars(["SKM"])[0]
    a = jpeg(4)
    make(tmp_path, {r.url: [FakeResp(a)]}).run([r])
    res = make(tmp_path, {r.url: [FakeResp(a)]}).run([r])[0]
    assert res.status == "duplicate"


def test_switch_off_stops_collection_unless_forced(tmp_path, monkeypatch):
    from cpmosaic import control
    from cpmosaic.s1_collect import __main__ as cli
    control.set_state(False, "dry season", "test", root=tmp_path)
    assert control.is_enabled(tmp_path) is False
    st = (tmp_path / "web/public/data/status.json").read_text(encoding="utf-8")
    assert '"paused_loop_last_forecast"' in st
    real = control.is_enabled
    monkeypatch.setattr(control, "is_enabled", lambda root=None: real(tmp_path))
    called = []
    monkeypatch.setattr(cli.Collector, "run", lambda self, rs, repeat, interval_s: called.append(1) or [])
    assert cli.main(["--root", str(tmp_path / "data"), "--repeat", "1"]) == 0 and called == []
    assert cli.main(["--root", str(tmp_path / "data"), "--repeat", "1", "--force"]) == 0 and called == [1]
    control.set_state(True, "trial", "test", root=tmp_path)
    assert control.is_enabled()


def test_switch_gha_output(tmp_path, monkeypatch):
    from cpmosaic import control
    out = tmp_path / "gh_out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    control.set_state(False, "", "", root=tmp_path)
    control.main(["status", "--gha", "--root", str(tmp_path)])
    control.main(["status", "--gha", "--force", "true", "--root", str(tmp_path)])
    assert out.read_text().split() == ["run=false", "run=true"]


def test_trial_report(tmp_path):
    r = radars(["PHS"])[0]
    a = jpeg(1)
    c = make(tmp_path, {r.url: [FakeResp(a), FakeResp(a), FakeResp(jpeg(2))]})
    c.run([r], repeat=3)
    rep = inventory.trial_report(inventory.load(tmp_path))
    row = rep.loc["PHS"]
    assert row["requests"] == 3 and row["new"] == 2 and row["duplicate"] == 1 and row["error"] == 0
    assert row["sizes"] == "400x300"


def test_status_bundle(tmp_path):
    import json
    from cpmosaic.s1_collect import status
    rs = radars(["PHS", "CRI"])
    url = {r.code: r.url for r in rs}
    plan = {url["PHS"]: [FakeResp(jpeg(1))], url["CRI"]: [FakeResp(b"<html>x</html>" * 100)]}
    make(tmp_path, plan).run(rs)
    h = status.update_history(tmp_path)
    assert len(h) == 2 and (tmp_path / "state" / "history.csv").exists()
    assert status.refresh_thumbs(tmp_path, h) == ["PHS"]
    from PIL import Image as _I
    assert _I.open(tmp_path / "state" / "thumbs" / "PHS.jpg").size == status.BOX
    assert len(list((tmp_path / "state" / "frames" / "PHS").glob("*.jpg"))) == 1
    d = status.build_site(tmp_path, tmp_path / "site", h)
    s = json.loads((d / "latest.json").read_text(encoding="utf-8"))
    by = {r["code"]: r for r in s["radars"]}
    assert len(by) == 9 and by["PHS"]["fresh"] and by["PHS"]["new_24h"] == 1
    assert by["CRI"]["err_24h"] == 1 and not by["CRI"]["fresh"]
    assert (d / "thumbs" / "PHS.jpg").exists() and (d / "history_48h.csv").exists()
    assert list(s["frames"]) == ["PHS"] and s["totals"]["images_7d"] == 1 and s["sizes"]["PHS"][0]["size"] == "400x300"
    # a second job with no new image keeps history and the old thumb
    h2 = status.update_history(tmp_path)
    assert len(h2) == 2
