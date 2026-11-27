# ตั้งที่เก็บภาพบน Google Drive (ทำครั้งเดียว)

ปลายทาง: Google Drive ของบัญชีวิจัย (5 TB) โฟลเดอร์ `ChaoPhraya_Radar_Archive`
ภาพราว 1.2 GB/วัน ≈ 440 GB/ปี และราว 860 ไฟล์/วัน

## 1. สร้าง client ID ของตัวเอง (กัน token หมดอายุ)

ถ้าใช้ client ID ของตัวเองแต่ปล่อยแอปไว้ในสถานะ Testing token จะหมดอายุทุก 7 วัน และ workflow จะหยุดส่งภาพเงียบๆ

1. https://console.cloud.google.com → สร้าง project ใหม่ เช่น `chaophraya-rain`
2. APIs & Services → Library → เปิด **Google Drive API**
3. OAuth consent screen → External → ใส่ชื่อแอปและอีเมลตัวเอง → บันทึก
4. ที่หน้า Audience / Publishing status กด **Publish app** ให้เป็น **In production** (ใช้เองคนเดียว ไม่ต้องส่ง verification)
5. Credentials → Create credentials → OAuth client ID → ชนิด **Desktop app** → จด client ID และ client secret

## 2. สร้าง remote ใน rclone (Windows)

```
winget install Rclone.Rclone
rclone config
```

ตอบตามนี้

| คำถาม | ตอบ |
|---|---|
| n/s/q | `n` |
| name | `gdrive` |
| Storage | `drive` |
| client_id / client_secret | ค่าจากข้อ 1 |
| scope | `drive.file` (เห็นเฉพาะไฟล์ที่ rclone สร้าง ถ้า secret รั่วก็แตะไฟล์อื่นในไดรฟ์ไม่ได้) |
| service_account_file | เว้นว่าง |
| Edit advanced config | `n` |
| Use web browser to automatically authenticate | `y` → ล็อกอินบัญชีที่มี 5 TB → ถ้าขึ้นเตือนให้กด Advanced → Go to ... (unsafe) |
| Configure this as a Shared Drive | `n` |

ทดสอบ

```
rclone mkdir gdrive:ChaoPhraya_Radar_Archive
rclone lsd gdrive:
```

## 3. ใส่ใน GitHub

PowerShell:

```
[Convert]::ToBase64String([IO.File]::ReadAllBytes("$env:APPDATA\rclone\rclone.conf")) | Set-Clipboard
```

repo → Settings → Secrets and variables → Actions

- New repository secret: `RCLONE_CONF` = วางจาก clipboard
- Variables → New repository variable: `ARCHIVE_REMOTE` = `gdrive:ChaoPhraya_Radar_Archive`

rclone.conf มี token ของไดรฟ์อยู่ อย่าส่งให้ใคร อย่าใส่ใน repo หรือ notebook

## 4. ตรวจ

Actions → s1-collect → Run workflow → ดูว่า step "Copy to archive" ผ่าน แล้วเปิดโฟลเดอร์ในไดรฟ์ควรเห็น `raw/ inventory/ state/`
ถ้าวันหนึ่ง step นี้เริ่มแดงด้วย `invalid_grant` แปลว่า token หมดอายุ ให้ตรวจข้อ 1.4 แล้วรัน `rclone config reconnect gdrive:` ใหม่
