# Chao Phraya Rain · ฝนลุ่มเจ้าพระยา

ระบบโมเสกเรดาร์และพยากรณ์ฝนระยะสั้น (nowcast) ของลุ่มน้ำเจ้าพระยา–ท่าจีน จากภาพเรดาร์ 9 สถานีที่กรมอุตุนิยมวิทยาเผยแพร่ทุก 15 นาที
แยกจากระบบทันฝน (TanFon, เรดาร์พิษณุโลกสถานีเดียว) แต่คงความสามารถเดิมไว้

Radar mosaic and 2-hour nowcast for the Chao Phraya–Tha Chin basin, built from the nine TMD radar images published
every 15 minutes. A separate system from TanFon (single PHS radar), keeping its features.

> ชื่อระบบ "Chao Phraya Rain / ฝนลุ่มเจ้าพระยา" เป็นชื่อทำงาน ยังไม่ยืนยัน · package `cpmosaic`

## สถานะ · Status

| Stage | ทำอะไร | สถานะ |
|---|---|---|
| s1_collect | ดึงภาพ HQ 9 สถานีทุก 15 นาที เก็บภาพใหม่ทุกภาพ | **ใช้งานได้** · มี test |
| s2_decode | อ่านเวลาสแกน (OCR), georeference, ภาพ → dBZ (4 layout) | วางแผน |
| s3_qc | interference, clutter, beam blockage, quality index | วางแผน |
| s4_mosaic | รวม 9 สถานี 4 วิธี (max, nearest, IDW, QI-weighted) | วางแผน |
| s5_nowcast | Extrapolation, S-PROG, STEPS, LINDA | วางแผน |
| s6_areal | ฝนรายลุ่มน้ำย่อย อำเภอ ตำบล (วิธีทันฝน) | วางแผน |
| s7_verify | เก็บคะแนนทุกพยากรณ์ (ไม่แสดงบนเว็บสาธารณะ) | วางแผน |
| s8_select | เลือก best product รายวันจากคะแนน 14 วัน | วางแผน |

เริ่มที่ s1 ก่อน เพราะ TMD เขียนทับภาพทุก 15 นาทีและไม่มี archive ภาพที่ไม่ได้ดึงไว้จะหายไปเลย

## เปิด/ปิดระบบ · System switch

นอกฤดูฝนปิดระบบได้ สถานะอยู่ใน `config/control.yaml` (ประวัติการเปิดปิด = git log ของไฟล์นี้)

- ปุ่มในหน้า admin `web/admin/index.html` หรือ Actions → **control** → Run workflow → เลือก on/off
- ปิดแล้ว: ทุก workflow หยุดหลังตรวจสวิตช์ ไม่เก็บภาพ หน้าสาธารณะวนแสดงพยากรณ์ชุดล่าสุดก่อนปิด (`web/public/data/status.json`)
- ทดสอบตอนปิดอยู่: Run workflow `s1-collect` ด้วย `force = true` หรือ `python -m cpmosaic.s1_collect --force`

## โครงสร้าง · Layout

ดู [docs/STRUCTURE.md](docs/STRUCTURE.md) และการตัดสินใจทั้งหมดใน [docs/DECISIONS.md](docs/DECISIONS.md)

## ติดตั้งและรัน · Run

```bash
pip install -e ".[dev]"
pytest -q                                          # offline tests
python -m cpmosaic.s1_collect --repeat 1           # one round, all nine radars, into ./data
python -m cpmosaic.s1_collect --radars PHS,CRI --repeat 1
```

บน Colab ใช้ `notebooks/01_collect_check.ipynb`

## เก็บภาพอัตโนมัติบน GitHub Actions

Workflow `.github/workflows/collect.yml` รันทุก 15 นาที ภาพดิบไม่เข้า git (ราว 12 MB ต่อรอบ, 1.2 GB ต่อวัน)
แต่ส่งขึ้นที่เก็บผ่าน rclone ตั้งค่าครั้งเดียวใน Settings → Secrets and variables → Actions:

| ชนิด | ชื่อ | ค่า |
|---|---|---|
| secret | `RCLONE_CONF` | base64 ของไฟล์ rclone.conf ที่มี remote ปลายทาง (สร้างด้วย `rclone config` ในเครื่องตัวเอง) |
| variable | `ARCHIVE_REMOTE` | เช่น `gdrive:ChaoPhraya_Radar_Archive` หรือ `r2:chaophraya-radar` |

ขั้นตอนตั้งค่าทีละข้อ: [docs/SETUP_ARCHIVE.md](docs/SETUP_ARCHIVE.md)

ถ้ายังไม่ตั้ง `RCLONE_CONF` ภาพจะเก็บเป็น artifact ของ workflow แค่ 7 วัน

ควรตั้ง repo เป็น **public** เพราะ job ละราว 10 นาที × 96 ครั้งต่อวัน เกินโควตานาทีฟรีของ repo แบบ private

cron ของ GitHub มักช้าหรือข้ามรอบ (เจอแล้วกับทันฝน) workflow นี้จึงเปิด `workflow_dispatch` ไว้ให้ตัวตั้งเวลาภายนอก เช่น cron-job.org เรียกได้เหมือนทันฝน

## ที่มาของข้อมูล · Data

ภาพเรดาร์: กรมอุตุนิยมวิทยา (`weather.tmd.go.th/<code>/<code>240_HQ_latest.jpg`) · พิกัดสถานี: `config/radars.yaml`
ขอบเขต: RTSD ผ่าน OCHA HDX, HydroBASINS/HydroRIVERS (Lehner & Grill 2013), Natural Earth
