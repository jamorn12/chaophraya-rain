# โครงสร้าง repo · Repository layout

```
chaophraya-rain/
├── README.md
├── pyproject.toml            package cpmosaic (pip install -e .)
├── requirements.txt
├── config/                   ค่าตั้งทั้งหมดอยู่ที่นี่ ไม่ฝังในโค้ด
│   ├── control.yaml          สวิตช์เปิด/ปิดระบบ (เปลี่ยนผ่าน workflow control)
│   ├── radars.yaml           9 สถานี: พิกัด ความคลาดเคลื่อน layout ผลิตภัณฑ์ URL
│   ├── collect.yaml          stage 1: timeout retry repeat interval
│   ├── domain.yaml           ลุ่มน้ำ + 50 km, AEQD 1 km, 15 นาที
│   └── select.yaml           stage 8: กฎเลือก best product v1
├── src/cpmosaic/
│   ├── config.py             อ่าน YAML, คลาส Radar
│   ├── control.py            อ่าน/ตั้งสวิตช์ เขียน web/public/data/status.json
│   ├── s1_collect/           ดึงภาพ ตรวจไฟล์ กันซ้ำด้วย hash เขียน inventory   ← ใช้งานได้
│   ├── s2_decode/            OCR เวลา, georeference, ภาพ → dBZ
│   ├── s3_qc/                QC รายสถานี + quality index
│   ├── s4_mosaic/            รวม 9 สถานี 4 วิธี
│   ├── s5_nowcast/           pySTEPS 4 โมเดล
│   ├── s6_areal/             ฝนรายลุ่มน้ำย่อย อำเภอ ตำบล
│   ├── s7_verify/            คะแนนทุกพยากรณ์
│   └── s8_select/            best product รายวัน
├── notebooks/                notebook เป็นตัวเรียกใช้ .py เท่านั้น (Colab ได้)
├── tests/                    test แบบ offline
├── web/
│   ├── public/               เว็บสาธารณะ ไทย/EN (data/status.json บอกโหมด live / พัก)
│   └── admin/                ฝั่งผู้เชี่ยวชาญ ไม่ลิงก์จากหน้าสาธารณะ (index.html: ปุ่มเปิดปิด + รอบเก็บภาพ)
├── docs/
│   ├── STRUCTURE.md          ไฟล์นี้
│   ├── DECISIONS.md          สิ่งที่ตัดสินใจแล้ว
│   └── figures/              กรอบแนวคิด
└── .github/workflows/
    ├── collect.yml           ทุก 15 นาที → rclone remote (ข้ามเมื่อสวิตช์ปิด)
    ├── control.yml           เปิด/ปิดระบบ
    └── tests.yml             test ทุก push
```

## ข้อมูล (ไม่อยู่ใน git) · Data, outside git

ทุก stage เขียนลง `data/` ในเครื่องที่รัน แล้ว workflow คัดลอกไปที่ `ARCHIVE_REMOTE` ด้วยโครงเดียวกัน

```
data/
├── raw/<CODE>/<YYYY>/<MM>/<DD>/<CODE>_<YYYYmmddTHHMMSS>Z_<sha8>.jpg   เวลา = เวลาที่ดึง (UTC)
├── inventory/<YYYY>/<MM>/<DD>/run_<HHMMSS>Z.csv                     1 ไฟล์ต่อ job
├── state/last_hash.json                                             hash ล่าสุดของแต่ละสถานี
├── decoded/  qc/  mosaic/  nowcast/  areal/  verify/                stage 2–7
└── selection/current.json, history.csv                              stage 8
```

## กติกา · Conventions

- เวลาในไฟล์และชื่อไฟล์เป็น UTC ทั้งหมด แปลงเป็นเวลาไทยตอนแสดงผลเท่านั้น
- โค้ดกระบวนการเป็น `.py` ใน `src/cpmosaic/`; notebook แค่เรียกใช้
- ไม่ลบภาพดิบ ทุก stage ต่อจากนี้สร้างซ้ำได้จาก `raw/` + `config/`
- ตัวอักษรในรูปเป็นภาษาอังกฤษ
- ไม่เก็บ token หรือรหัสใดๆ ใน repo (ใช้ GitHub secrets)
