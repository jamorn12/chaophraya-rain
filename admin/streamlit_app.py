"""ฝนลุ่มเจ้าพระยา · ระบบจัดการเรดาร์ 9 สถานี — หน้าหลังบ้าน (Streamlit)

หน้าตาเดียวกับหลังบ้านทันฝน: แถบหัวกรมท่า + แถบเครื่องมือ (ชั้นข้อมูล + สถานี) + ตารางสถานะ + การ์ดควบคุม + กราฟ 48 ชม.

อ่านข้อมูลจาก GitHub Pages ของ repo (data/status/: latest.json, history_48h.csv, thumbs/) และ GitHub API
ไม่ต่อ Google Drive โดยตรง ภาพเต็มอยู่ในคลังบนไดรฟ์

Secrets (Streamlit Cloud > App settings > Secrets):
  GITHUB_TOKEN = "github_pat_..."   fine-grained, เฉพาะ repo chaophraya-rain, Actions: Read and write
                                     ไม่ใส่ก็ดูได้ แต่สวิตช์เปิด/ปิดระบบใช้ไม่ได้ และ API จำกัด 60 ครั้ง/ชม.
"""
from __future__ import annotations

import io
import time
from datetime import datetime, timedelta, timezone

import altair as alt
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="ฝนลุ่มเจ้าพระยา · ระบบจัดการเรดาร์", layout="wide", page_icon="📡",
                   initial_sidebar_state="collapsed")

# ------------------------------------------------------------------ ค่าตั้ง
TOKEN = str(st.secrets.get("GITHUB_TOKEN", "")).strip() if hasattr(st, "secrets") else ""
OWNER = st.secrets.get("REPO_OWNER", "jamorn12")
REPO = st.secrets.get("REPO_NAME", "chaophraya-rain")
API = f"https://api.github.com/repos/{OWNER}/{REPO}"
GH = f"https://github.com/{OWNER}/{REPO}"
WEB = f"https://{OWNER}.github.io/{REPO}/"
STATUS = st.secrets.get("STATUS_URL", f"{WEB}data/status/")
TH = timezone(timedelta(hours=7))
RUN_MINUTES = (0, 15, 30, 45)                   # cron */15 (เวลาที่สั่ง, GitHub อาจช้ากว่านี้)
STALE_MIN = 45
NAVY, OK, WARN, BAD, CORAL, TEAL = "#1d4e89", "#1a7f37", "#b35900", "#c0392b", "#ef5b3a", "#127c86"
TH_MON = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
TH_NAME = {"CRI": "เชียงราย", "LMP": "ลำพูน", "TAK": "ดอยมูเซอ ตาก", "PHS": "พิษณุโลก", "PHB": "วิเชียรบุรี เพชรบูรณ์",
           "CHN": "ชัยนาท", "KKW": "นครนายก", "SVP": "สุวรรณภูมิ", "SKM": "สมุทรสงคราม"}
CODES = list(TH_NAME)

HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

# ------------------------------------------------------------------ หน้าตา (เหมือนหลังบ้านทันฝน)
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&family=IBM+Plex+Mono:wght@500&display=swap');
html,body,[class*="css"],.stMarkdown,button,input,label{{font-family:'Sarabun',sans-serif!important}}
.stApp{{background:#fff}}
header[data-testid="stHeader"]{{display:none}}
.block-container,[data-testid="stMainBlockContainer"]{{padding:0 18px 28px!important;max-width:100%!important}}
[data-testid="stAppViewContainer"] .main,[data-testid="stMain"]{{padding-top:0!important}}
.mono{{font-family:'IBM Plex Mono',monospace}}
.topbar{{margin:0 -18px;height:48px;background:{NAVY};color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 20px}}
.topbar b{{font-size:17px}} .topbar .sub{{opacity:.85;margin-left:10px;padding-left:10px;border-left:1px solid #ffffff55}}
.topbar .r{{font-size:13px;opacity:.9}}
@media (max-width:700px){{.topbar{{height:auto;padding:10px 16px;flex-direction:column;align-items:flex-start;gap:2px}}
  .topbar .sub{{display:block;margin:0;padding:0;border:none;font-size:13px}} .topbar .r{{font-size:11.5px}}}}
div[data-testid="stHorizontalBlock"]:has(> div .tb-anchor){{background:#f4f6f9;margin:0 -18px 16px;padding:10px 18px 6px;border-bottom:1px solid #d7dde5}}
h3.sec{{font-size:16px;font-weight:700;border-left:5px solid {NAVY};padding-left:9px;margin:4px 0 10px;color:#222}}
.note{{font-size:12.5px;color:#666}}
table.gv{{border-collapse:collapse;width:100%;font-size:14px}}
table.gv th,table.gv td{{border:1px solid #d7dde5;padding:7px 10px;text-align:left}}
table.gv th{{background:#eef2f7;font-weight:600}}
table.gv.st th{{width:33%}}
table.gv.lg td{{font-family:'IBM Plex Mono',monospace;font-size:13px}}
table.gv td.n{{text-align:right;font-family:'IBM Plex Mono',monospace;font-size:13px}}
.badge{{display:inline-block;padding:7px 14px;border-radius:4px;color:#fff;font-weight:700;font-size:14px;white-space:nowrap}}
.links a{{color:{NAVY};margin-right:18px;font-size:14px;text-decoration:none}}
.cap{{font-size:13px;color:#555;margin:2px 0 4px}} .cap b{{color:#222}}
div[data-testid="stImage"] img{{border:1px solid #c9d3df}}
div[data-testid="stButtonGroup"] button{{border:2px solid {NAVY}!important;color:{NAVY}!important;border-radius:999px!important;
  background:#fff!important;font-weight:600;margin-right:4px}}
div[data-testid="stButtonGroup"] button[aria-checked="true"],div[data-testid="stButtonGroup"] button[kind$="Active"]{{background:{NAVY}!important;color:#fff!important}}
.legend span{{margin-right:14px;font-size:12.5px;color:#555}}
.legend i{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}}
.ph{{border:1px dashed #c9d3df;border-radius:6px;padding:28px 18px;color:#666;font-size:14px;line-height:1.7;background:#fafbfd}}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ ตัวช่วยเวลา
def ts(s):
    return None if s is None or (isinstance(s, float) and pd.isna(s)) else pd.Timestamp(s).tz_convert("UTC")


def th_str(dt, date=True, year=False) -> str:
    if dt is None or pd.isna(dt):
        return "—"
    dt = dt.astimezone(TH)
    y = f" {dt.year + 543}" if year else ""
    return f"{dt.day} {TH_MON[dt.month]}{y} {dt:%H:%M} น." if date else f"{dt:%H:%M} น."


def age_min(dt) -> float | None:
    return None if dt is None else (datetime.now(timezone.utc) - dt).total_seconds() / 60


def age_str(m: float | None) -> str:
    if m is None:
        return "—"
    t = int(round(m))
    return f"{t} นาที" if t < 60 else (f"{t // 60} ชม. {t % 60} นาที" if t < 1440 else f"{t // 1440} วัน")


def next_run() -> datetime:
    n = datetime.now(TH)
    m = next((x for x in RUN_MINUTES if x > n.minute), None)
    return (n.replace(minute=m, second=0, microsecond=0) if m is not None
            else (n + timedelta(hours=1)).replace(minute=RUN_MINUTES[0], second=0, microsecond=0))


# ------------------------------------------------------------------ ดึงข้อมูล
def _get(url, timeout=8, **kw):
    try:
        r = requests.get(url, headers=HEADERS if url.startswith(API) else None, timeout=timeout, **kw)
        return r if r.status_code == 200 else None
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def load_status() -> dict | None:
    r = _get(f"{STATUS}latest.json?t={int(time.time())}")
    try:
        return r.json() if r else None
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def load_hist() -> pd.DataFrame:
    try:
        h = pd.read_csv(f"{STATUS}history_48h.csv?t={int(time.time())}", dtype={"error": str})
    except Exception:
        return pd.DataFrame()
    h["t"] = pd.to_datetime(h["fetch_utc"], utc=True, errors="coerce")
    return h.dropna(subset=["t"]).sort_values("t").reset_index(drop=True)


@st.cache_data(ttl=120, show_spinner=False)
def load_runs(wf: str, n: int = 12) -> list[dict]:
    r = _get(f"{API}/actions/workflows/{wf}/runs", params={"per_page": n})
    return r.json().get("workflow_runs", []) if r else []


@st.cache_data(ttl=300, show_spinner=False)
def thumb(code: str, version: str) -> bytes | None:
    r = _get(f"{STATUS}thumbs/{code}.jpg?v={version}", timeout=12)
    return r.content if r else None


def set_switch(on: bool, reason: str) -> tuple[bool, str]:
    try:
        r = requests.post(f"{API}/actions/workflows/control.yml/dispatches", headers=HEADERS, timeout=8,
                          json={"ref": "main", "inputs": {"state": "on" if on else "off", "reason": reason}})
        return r.status_code == 204, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


# ------------------------------------------------------------------ ประเมินสถานะรวม
def overall(S, runs, sched_age):
    if S is None:
        return BAD, "อ่านสถานะไม่ได้"
    if not S["control"]["enabled"]:
        return WARN, "ปิดระบบอยู่"
    fresh = sum(r["fresh"] for r in S["radars"])
    if fresh == 0:
        return BAD, "ไม่มีภาพใหม่"
    if fresh < len(S["radars"]):
        return WARN, f"ภาพเข้า {fresh}/{len(S['radars'])} สถานี"
    if runs and runs[0].get("conclusion") == "failure":
        return WARN, "รอบล่าสุดล้มเหลว"
    if sched_age is None or sched_age > 60:
        return WARN, "cron ไม่ทำงาน"
    return OK, "ระบบทำงานปกติ"


# ------------------------------------------------------------------ ส่วนประกอบ
def status_table(S, H, runs, sched):
    rows = []
    if S:
        fresh = sum(r["fresh"] for r in S["radars"])
        newest = max((ts(r["last_new_utc"]) for r in S["radars"] if r["last_new_utc"]), default=None)
        rows.append(("ภาพเรดาร์ล่าสุด", f"{th_str(newest, year=True)} ({age_str(age_min(newest))}) · สด {fresh}/9 สถานี",
                     ("ปกติ", OK) if fresh == 9 else (("บางสถานี", WARN) if fresh else ("ค้าง", BAD))))
        got = sum(r["new_24h"] for r in S["radars"])
        worst = min(S["radars"], key=lambda r: r["new_24h"])
        rows.append(("ความครบ 24 ชม.", f"{got:,} / {9 * 96:,} ภาพ · น้อยสุด {worst['code']} {worst['new_24h']}/96",
                     ("ครบ", OK) if worst["new_24h"] >= 92 else (("ขาดบางช่อง", WARN) if worst["new_24h"] >= 70 else ("ขาดมาก", BAD))))
        c = S["control"]
        rows.append(("สวิตช์ระบบ", f"{'เปิด' if c['enabled'] else 'ปิด'} · ตั้งเมื่อ {th_str(ts(c['changed_utc']))} · {c.get('reason') or '—'}",
                     ("ON", OK) if c["enabled"] else ("OFF", WARN)))
    if runs:
        run = runs[0]
        cc = run.get("conclusion") or run.get("status")
        rt = pd.to_datetime(run["run_started_at"], utc=True)
        dur = (pd.to_datetime(run["updated_at"]) - rt).total_seconds()
        okn = sum(1 for r in runs if r.get("conclusion") == "success")
        rows.append(("pipeline", f"#{run['run_number']} · {th_str(rt, False)} · {int(dur // 60)} นาที {int(dur % 60)} วินาที",
                     {"success": (f"สำเร็จ {okn}/{len(runs)}", OK), "failure": ("ล้มเหลว", BAD)}.get(cc, (str(cc), WARN))))
    else:
        rows.append(("pipeline", "อ่าน GitHub API ไม่ได้", ("—", "#888")))
    rows.append(("รอบตามเวลา (cron)", f"ล่าสุด {th_str(sched)} ({age_str(age_min(sched))})" if sched else "ยังไม่เคยรันตามเวลา",
                 ("ปกติ", OK) if sched and age_min(sched) <= 60 else ("ไม่ทำงาน", WARN)))
    if S and S.get("archive"):
        a = S["archive"]
        rows.append(("คลังภาพ", f'<a href="{a["url"]}" target="_blank">{a["label"]}</a>', ("ต่ออยู่", OK)))
    body = "".join(f'<tr><th>{a}</th><td>{b}</td><td style="color:{c[1]};font-weight:700">{c[0]}</td></tr>' for a, b, c in rows)
    st.markdown(f'<table class="gv st">{body}</table>', unsafe_allow_html=True)


def station_table(S):
    if not S:
        return
    rows = ""
    for r in S["radars"]:
        t = ts(r["last_new_utc"])
        col, txt = (OK, "สด") if r["fresh"] else ((BAD, "ค้าง") if t else ("#888", "ยังไม่มี"))
        rows += (f'<tr><td><b>{r["code"]}</b> {TH_NAME.get(r["code"], r["name"])}</td><td>{th_str(t, False)}</td>'
                 f'<td class="n">{age_str(r["age_min"])}</td><td class="n">{r["new_24h"]}</td><td class="n">{r["err_24h"]}</td>'
                 f'<td style="color:{col};font-weight:700">{txt}</td></tr>')
    st.markdown('<table class="gv"><tr><th>สถานี</th><th>ภาพล่าสุด</th><th>อายุ</th><th>24 ชม.</th><th>ผิดพลาด</th><th></th></tr>'
                f'{rows}</table>', unsafe_allow_html=True)


def control_card(S):
    with st.container(border=True):
        st.markdown(f'<div style="font-weight:700;font-size:15px;color:{NAVY};margin-bottom:8px">⏻ ควบคุมระบบ</div>',
                    unsafe_allow_html=True)
        enabled = S["control"]["enabled"] if S else None
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        nr = next_run()
        c1.markdown(f'<div><b style="font-size:15px">เก็บภาพ 9 สถานีอัตโนมัติ</b><div class="note">ทุก 15 นาที · :00 :15 :30 :45 · '
                    f'รอบถัดไป {nr:%H:%M} น. · ปิดนอกฤดูฝนได้ (หน้าสาธารณะจะวนพยากรณ์ชุดล่าสุด)</div></div>',
                    unsafe_allow_html=True)
        if not TOKEN or enabled is None:
            c2.toggle("เปิด", value=bool(enabled), disabled=True, label_visibility="collapsed")
            st.markdown('<div class="note">ใส่ GITHUB_TOKEN ใน Secrets ของแอป (fine-grained · เฉพาะ repo นี้ · Actions: Read and write) '
                        'เพื่อเปิด/ปิดจากหน้านี้ หรือสั่งที่ Actions › control › Run workflow</div>', unsafe_allow_html=True)
        else:
            pending = st.session_state.get("pending")
            on = c2.toggle("เปิด", value=enabled if pending is None else pending, label_visibility="collapsed")
            if on != enabled and pending is None:
                ok, msg = set_switch(on, "admin page")
                if ok:
                    st.session_state["pending"] = on
                    st.toast("ส่งคำสั่งเปิดระบบแล้ว" if on else "ส่งคำสั่งปิดระบบแล้ว · รอ workflow control ราว 1 นาที", icon="✅")
                else:
                    st.error(f"สั่งไม่สำเร็จ ({msg}) ตรวจสิทธิ์ของ token")
            if pending is not None:
                if pending == enabled:
                    st.session_state.pop("pending")
                else:
                    st.markdown('<div class="note">⏳ รอ workflow control ทำงาน แล้วกดรีเฟรช</div>', unsafe_allow_html=True)
        a, b = st.columns(2)
        a.link_button("เว็บสาธารณะ", WEB, icon=":material/public:", width="stretch")
        b.link_button("Actions", f"{GH}/actions", icon=":material/account_tree:", width="stretch")
        a.link_button("คลังภาพ (Drive)", (S or {}).get("archive", {}).get("url", GH), icon=":material/folder:", width="stretch")
        if b.button("รีเฟรช", icon=":material/refresh:", width="stretch"):
            st.cache_data.clear()
            st.rerun()


def chart_48h(H, height=230):
    end = pd.Timestamp.now(tz="UTC").floor("15min")
    slots = pd.date_range(end - pd.Timedelta(hours=48), end, freq="15min")
    if len(H):
        h = H.assign(slot=H["t"].dt.floor("15min"))
        rank = {"new": 3, "error": 2, "duplicate": 1}
        h["k"] = h["status"].map(rank).fillna(0)
        g = h.groupby(["code", "slot"])["k"].max().unstack(fill_value=0).reindex(index=CODES, columns=slots, fill_value=0)
    else:
        g = pd.DataFrame(0, index=CODES, columns=slots)
    lab = {3: "ภาพใหม่", 2: "ผิดพลาด", 1: "ภาพซ้ำ (ยังไม่อัปเดต)", 0: "ไม่มีรอบ"}
    t = g.stack().rename("k").reset_index().rename(columns={"level_1": "slot", "level_0": "code"})
    t.columns = ["code", "slot", "k"]
    t["slot"] = t["slot"].dt.tz_convert(TH).dt.tz_localize(None)
    t["end"] = t["slot"] + pd.Timedelta(minutes=15)
    t["สถานะ"] = t["k"].map(lab)
    ch = alt.Chart(t).mark_rect(stroke="#fff", strokeWidth=0.3).encode(
        x=alt.X("slot:T", title=None, axis=alt.Axis(format="%d %b %H:%M", labelColor="#666", grid=False, tickCount=4)),
        x2="end:T",
        y=alt.Y("code:N", title=None, sort=CODES, axis=alt.Axis(labelColor="#444")),
        color=alt.Color("สถานะ:N", legend=None, scale=alt.Scale(
            domain=[lab[3], lab[1], lab[2], lab[0]], range=[TEAL, "#a9d6da", CORAL, "#f1f3f6"])),
        tooltip=[alt.Tooltip("code:N", title="สถานี"), alt.Tooltip("slot:T", title="ช่องเวลา", format="%d/%m %H:%M"),
                 alt.Tooltip("สถานะ:N")]).properties(height=height)
    st.altair_chart(ch.configure_view(strokeWidth=0), width="stretch")
    miss = int((g == 0).values.sum())
    st.markdown(f'<div class="legend"><span><i style="background:{TEAL}"></i>ภาพใหม่</span><span><i style="background:#a9d6da"></i>ภาพซ้ำ</span>'
                f'<span><i style="background:{CORAL}"></i>ผิดพลาด</span><span><i style="background:#e3e7ec"></i>ไม่มีรอบ {miss}/{g.size} ช่อง</span></div>',
                unsafe_allow_html=True)


def log_table(H, code=None, n=10):
    if not len(H):
        st.markdown('<div class="note">ยังไม่มีบันทึก</div>', unsafe_allow_html=True)
        return
    v = (H if code is None else H[H["code"] == code]).tail(n).iloc[::-1]
    col = {"new": OK, "duplicate": "#888", "error": BAD}
    rows = "".join(
        f'<tr><td>{th_str(r.t)}</td><td>{r.code}</td><td style="color:{col.get(r.status, "#444")}">{r.status}</td>'
        f'<td class="n">{(r.bytes or 0) / 1e6:.2f}</td><td class="n">{"" if pd.isna(r.width) or not r.width else f"{int(r.width)}×{int(r.height)}"}</td>'
        f'<td class="n">{"" if pd.isna(r.http_status) or not r.http_status else int(r.http_status)}</td>'
        f'<td style="font-size:12px">{"" if pd.isna(r.error) else str(r.error)[:80]}</td></tr>' for r in v.itertuples())
    st.markdown('<table class="gv lg"><tr><th>เวลาดึง</th><th>สถานี</th><th>ผล</th><th>MB</th><th>ขนาดภาพ</th><th>HTTP</th><th>ข้อผิดพลาด</th></tr>'
                f'{rows}</table>', unsafe_allow_html=True)


def runs_table(runs, title):
    st.markdown(f'<h3 class="sec">{title}</h3>', unsafe_allow_html=True)
    if not runs:
        st.info("อ่าน GitHub API ไม่ได้ หรือยังไม่มีรอบ")
        return
    mark = {"success": ("สำเร็จ", OK), "failure": ("ล้มเหลว", BAD), "cancelled": ("ยกเลิก", "#888"), "skipped": ("ข้าม", "#888")}
    ev = {"workflow_dispatch": "สั่งเอง/ตัวตั้งเวลา", "schedule": "cron", "push": "push"}
    rows = ""
    for r in runs:
        c = mark.get(r.get("conclusion"), ("กำลังรัน", NAVY))
        st_ = pd.to_datetime(r["run_started_at"], utc=True)
        dur = (pd.to_datetime(r["updated_at"]) - st_).total_seconds() if r.get("conclusion") else None
        rows += (f'<tr><td><a href="{r["html_url"]}" target="_blank">#{r["run_number"]}</a></td><td>{th_str(st_)}</td>'
                 f'<td>{"—" if dur is None else f"{int(dur // 60)}:{int(dur % 60):02d}"}</td><td>{ev.get(r.get("event"), r.get("event"))}</td>'
                 f'<td style="color:{c[1]};font-weight:700">{c[0]}</td></tr>')
    st.markdown('<table class="gv"><tr><th>รอบ</th><th>เริ่ม</th><th>ใช้เวลา</th><th>สั่งโดย</th><th>ผล</th></tr>'
                f'{rows}</table>', unsafe_allow_html=True)


def placeholder(stage, text):
    st.markdown(f'<div class="ph"><b>{stage} ยังไม่เปิดใช้</b><br>{text}</div>', unsafe_allow_html=True)


def radar_card(r, big=False):
    t = ts(r["last_new_utc"])
    col = OK if r["fresh"] else (BAD if t else "#888")
    st.markdown(f'<div class="cap"><b>{r["code"]}</b> {TH_NAME.get(r["code"], r["name"])} · '
                f'<span style="color:{col}">{th_str(t, False)} ({age_str(r["age_min"])})</span></div>', unsafe_allow_html=True)
    b = thumb(r["code"], r["last_new_utc"] or "none") if t else None
    if b:
        st.image(b, width="stretch")
    else:
        st.markdown('<div style="aspect-ratio:6/5;border:1px dashed #c9d3df;display:grid;place-items:center;color:#888;font-size:13px">'
                    'ยังไม่มีภาพ</div>', unsafe_allow_html=True)
    if big:
        st.markdown(f'<div class="note" style="margin-top:6px">ผลิตภัณฑ์ {r["product"]} · layout {r["layout"]} · ภาพ {r["size"] or "—"} · '
                    f'{(r["bytes"] or 0) / 1e6:.2f} MB · พิกัด {r["lat"]:.4f}, {r["lon"]:.4f}'
                    f'{" · ผิดพลาดล่าสุด: " + r["last_error"] if r["last_error"] else ""}</div>', unsafe_allow_html=True)


# ================================================================== จัดหน้า
S, H = load_status(), load_hist()
runs = load_runs("collect.yml")
sched = next((pd.to_datetime(r["run_started_at"], utc=True) for r in runs if r.get("event") == "schedule"), None)
badge = overall(S, runs, age_min(sched))

st.markdown(f"""<div class="topbar"><div><b>📡 ฝนลุ่มเจ้าพระยา</b><span class="sub">ระบบจัดการเรดาร์ 9 สถานี · ลุ่มเจ้าพระยา–ท่าจีน</span></div>
<div class="r">ข้อมูล ณ {th_str(datetime.now(timezone.utc), year=True)} · <span class="mono">{OWNER}/{REPO}</span></div></div>""",
            unsafe_allow_html=True)

LAYERS = {"ภาพดิบ": ":material/image:", "หลัง QC": ":material/grid_view:", "Mosaic": ":material/layers:",
          "พยากรณ์": ":material/rainy:", "คุณภาพ": ":material/monitoring:", "pipeline": ":material/account_tree:"}
tb = st.columns([6.2, 2.4, 1.8], vertical_alignment="center")
with tb[0]:
    st.markdown('<span class="tb-anchor"></span>', unsafe_allow_html=True)
    layer = st.segmented_control("ชั้นข้อมูล", list(LAYERS), default="ภาพดิบ", label_visibility="collapsed",
                                 format_func=lambda k: f"{LAYERS[k]} {k}") or "ภาพดิบ"
with tb[1]:
    station = st.selectbox("สถานี", ["ทั้งหมด"] + CODES, label_visibility="collapsed",
                           format_func=lambda c: "ทุกสถานี (9)" if c == "ทั้งหมด" else f"{c} · {TH_NAME[c]}")
with tb[2]:
    st.markdown(f'<div style="text-align:right"><span class="badge" style="background:{badge[0]}">● {badge[1]}</span></div>',
                unsafe_allow_html=True)

left, right = st.columns([1.05, 1], gap="large")
by = {r["code"]: r for r in (S or {}).get("radars", [])}

with left:
    if layer == "ภาพดิบ":
        if not S:
            st.warning("ยังอ่านสถานะจาก GitHub Pages ไม่ได้")
        elif station == "ทั้งหมด":
            st.markdown('<h3 class="sec">ภาพล่าสุดจากกรมอุตุฯ · 9 สถานี</h3>', unsafe_allow_html=True)
            for i in range(0, 9, 3):
                cols = st.columns(3, gap="small")
                for c, code in zip(cols, CODES[i:i + 3]):
                    with c:
                        radar_card(by[code])
        else:
            st.markdown(f'<h3 class="sec">{station} {TH_NAME[station]} · ภาพล่าสุด</h3>', unsafe_allow_html=True)
            radar_card(by[station], big=True)
        st.write("")
        st.markdown('<h3 class="sec">บันทึกรายรอบ</h3>', unsafe_allow_html=True)
        log_table(H, None if station == "ทั้งหมด" else station)
    elif layer == "หลัง QC":
        st.markdown('<h3 class="sec">หลังแยกชั้นแผนที่และ QC</h3>', unsafe_allow_html=True)
        placeholder("ขั้น s2–s3", "อ่านเวลาสแกนจากภาพ (OCR) · ตรึงพิกัด · แปลงสีเป็น dBZ ตาม 4 รูปแบบภาพ · QC (RFI, clutter, beam blockage)<br>"
                    "เมื่อเปิดใช้ หน้านี้จะแสดงภาพก่อน/หลัง QC รายสถานี และค่า echo %, max dBZ, RFI ที่ตัด")
    elif layer == "Mosaic":
        st.markdown('<h3 class="sec">Mosaic 9 สถานี</h3>', unsafe_allow_html=True)
        placeholder("ขั้น s4", "รวม 9 สถานีเป็นกริด 1 กม. ทั้งลุ่มน้ำ 4 วิธี (max, nearest, IDW, quality-weighted)")
    elif layer == "พยากรณ์":
        st.markdown('<h3 class="sec">พยากรณ์ล่วงหน้า 2 ชั่วโมง</h3>', unsafe_allow_html=True)
        placeholder("ขั้น s5–s8", "Extrapolation · S-PROG · STEPS · LINDA · เลือก best product รายวันจากคะแนน 14 วัน")
    elif layer == "คุณภาพ":
        st.markdown('<h3 class="sec">การเก็บภาพ 48 ชั่วโมง · รายสถานี</h3>', unsafe_allow_html=True)
        chart_48h(H, height=320)
        st.write("")
        st.markdown('<h3 class="sec">บันทึกรายรอบ</h3>', unsafe_allow_html=True)
        log_table(H, None if station == "ทั้งหมด" else station, n=20)
    else:
        runs_table(runs, "s1-collect 12 รอบหลังสุด")
        st.write("")
        runs_table(load_runs("control.yml", 6), "ประวัติการเปิด/ปิดระบบ")

with right:
    st.markdown('<h3 class="sec">สถานะระบบ</h3>', unsafe_allow_html=True)
    status_table(S, H, runs, sched)
    st.write("")
    control_card(S)
    if layer != "คุณภาพ":
        with st.container(border=True):
            st.markdown(f'<div style="font-weight:700;font-size:15px;color:{NAVY}">〽 48 ชั่วโมงล่าสุด</div>', unsafe_allow_html=True)
            chart_48h(H)
    st.markdown('<h3 class="sec">รายสถานี</h3>', unsafe_allow_html=True)
    station_table(S)
    st.markdown(f'<div class="links" style="margin-top:12px"><a href="{WEB}" target="_blank">› เว็บสาธารณะ</a>'
                f'<a href="{GH}/actions" target="_blank">› GitHub Actions</a><a href="{GH}" target="_blank">› repo</a></div>',
                unsafe_allow_html=True)
