# Gold Signal Tracker — คู่มือติดตั้งและ Deploy

---

## ขั้นตอนที่ 1 — ขอ API Keys

### 1.1 Telegram API (ฟรี, จำเป็นต้องมี)
1. เปิด https://my.telegram.org/apps
2. Login ด้วยเบอร์โทรศัพท์
3. กด **Create New Application**
4. กรอกข้อมูล (ชื่อ app อะไรก็ได้)
5. คัดลอก **App api_id** และ **App api_hash**

### 1.2 Claude API (จำเป็น — มีเครดิตฟรีตอนสมัครใหม่)
1. เปิด https://console.anthropic.com
2. สมัครบัญชี → ไปที่ **API Keys**
3. กด **Create Key** → คัดลอก key
4. ใช้ model `claude-haiku-4-5-20251001` (ถูกที่สุด ~$0.001/1,000 messages)

### 1.3 Supabase (ฟรี — ใช้ฐานข้อมูลที่มีอยู่แล้วได้)
1. เปิด https://app.supabase.com → เลือก Project ที่มีอยู่
2. ไปที่ **Settings → API**
3. คัดลอก **Project URL** และ **anon / public key**
4. ไปที่ **SQL Editor** → วางเนื้อหาจากไฟล์ `backend/migrations/001_create_tables.sql` → กด **Run**
   - สร้างตาราง: `gold_channels`, `gold_signals`, `gold_prices`

### 1.4 Twelve Data API (แนะนำ — ฟรี 800 req/วัน)
1. เปิด https://twelvedata.com
2. สมัครบัญชี → ไปที่ **API Keys** → คัดลอก key
3. หากไม่มี → ระบบจะ fallback ไป Alpha Vantage → yfinance (delay 15 นาที)

### 1.5 Alpha Vantage (สำรอง — ฟรี 25 req/วัน)
1. เปิด https://alphavantage.co/support/#api-key
2. กรอก email → รับ key ทันที

---

## ขั้นตอนที่ 2 — ติดตั้งบนเครื่อง (Local)

```bash
# ไปที่โฟลเดอร์โปรเจค
cd "D:/gold signal tracker"

# สร้าง .env จาก template
copy .env.example backend\.env
# เปิด backend\.env แล้วใส่ค่าจริงทุกตัว
```

**ค่าที่ต้องแก้ใน `.env`:**
```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_CHANNELS=channel1,channel2
CLAUDE_API_KEY=sk-ant-...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJhbGci...
TWELVE_DATA_KEY=abc123
API_SECRET_KEY=ตั้งเป็น random string ยาว 32 ตัวอักษร
```

```bash
# ── Backend ──────────────────────────────────────
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
python main.py
# เปิด browser: http://localhost:8000/docs
```

### ครั้งแรกที่รัน — Telegram Login
```
ระบบจะถาม: Please enter your phone number: +66xxxxxxxxx
ระบบจะถาม: Please enter the code you received: 12345
(รับ OTP จาก Telegram)
หลังจากนั้น session จะถูก save → ไม่ต้อง login ซ้ำ
```

```bash
# ── Frontend (terminal ใหม่) ──────────────────────
cd "D:/gold signal tracker/frontend"
npm install
npm run dev
# เปิด browser: http://localhost:5173
```

---

## ขั้นตอนที่ 3 — Deploy Frontend (GitHub Pages — ฟรี)

### 3.1 สร้าง GitHub Repository
1. ไปที่ https://github.com/new
2. สร้าง repo ชื่ออะไรก็ได้ เช่น `gold-signal-tracker`
3. Push code ขึ้น:
```bash
cd "D:/gold signal tracker"
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/gold-signal-tracker.git
git push -u origin main
```

### 3.2 ตั้งค่า GitHub Secrets
ไปที่ **Settings → Secrets and variables → Actions → New secret**:

| Secret Name      | ค่า                                              |
|-----------------|--------------------------------------------------|
| VITE_API_URL    | URL ของ backend เช่น `https://gold-api.render.com` |
| VITE_WS_URL     | WS URL เช่น `wss://gold-api.render.com`           |
| VITE_API_KEY    | ค่าเดียวกับ `API_SECRET_KEY` ใน .env               |
| VITE_BASE_PATH  | `/gold-signal-tracker/` (ชื่อ repo ของคุณ)         |

### 3.3 เปิด GitHub Pages
1. ไปที่ **Settings → Pages**
2. Source: **GitHub Actions**
3. Push code → frontend จะ build และ deploy อัตโนมัติ
4. URL: `https://YOUR_USERNAME.github.io/gold-signal-tracker/`

---

## ขั้นตอนที่ 4 — Deploy Backend (เลือก 1 อย่าง)

### ตัวเลือก A: Render.com (แนะนำ — ง่ายสุด)
1. เปิด https://render.com → สมัครฟรี
2. **New → Web Service → Connect GitHub**
3. เลือก repo → Render จะ detect `render.yaml` อัตโนมัติ
4. ไปที่ **Environment** → ใส่ค่า secret ทุกตัวจาก `.env`
5. กด **Deploy** → รอประมาณ 2–3 นาที
6. ⚠️ Free tier: spin down หลัง 15 นาที idle (request แรกช้า ~30s)

### ตัวเลือก B: Railway.app ($5 free credit/เดือน)
1. เปิด https://railway.app → สมัครด้วย GitHub
2. **New Project → Deploy from GitHub**
3. เลือก repo → Railway detect `railway.toml` อัตโนมัติ
4. ไปที่ **Variables** → เพิ่มค่าทุกตัวจาก `.env`
5. Deploy → URL จะได้เป็น `https://xxx.railway.app`
6. ✅ ไม่ spin down เหมือน Render

### ตัวเลือก C: รันบนเครื่องตัวเอง 24/7
```bash
npm install -g pm2
cd "D:/gold signal tracker/backend"
pm2 start "python main.py" --name gold-backend
pm2 save
pm2 startup
```

---

## ตรวจสอบว่าระบบทำงาน

```bash
# Test health check
curl http://localhost:8000/health

# Test API (ต้องใส่ key)
curl -H "X-API-Key: YOUR_SECRET_KEY" http://localhost:8000/api/signals

# ดู logs
type backend\gold_tracker.log       # Windows
# tail -f backend/gold_tracker.log  # Mac/Linux
```

---

## ปัญหาที่พบบ่อย

| ปัญหา | วิธีแก้ |
|-------|--------|
| `TELEGRAM_API_ID ไม่ได้ตั้งค่า` | เปิด `backend\.env` แก้ให้ถูกต้อง |
| Telegram login loop | ลบไฟล์ `gold_tracker_session.session` แล้วรันใหม่ |
| `Supabase error: relation does not exist` | รัน `migrations/001_create_tables.sql` ใน Supabase SQL Editor |
| `Invalid API Key` (401) | ตรวจ `API_SECRET_KEY` ใน `.env` ต้องตรงกับ `VITE_API_KEY` ใน GitHub Secrets |
| Frontend ต่อ API ไม่ได้ | ตรวจ CORS — `FRONTEND_URL` ใน `.env` ต้องตรงกับ URL จริงของ frontend |
| ไม่พบราคาทองคำ | ตรวจ `TWELVE_DATA_KEY` หรือรอ yfinance fetch รอบแรก (~1 นาที) |
| Chart ไม่แสดงข้อมูล | ต้องมีราคาในช่วงเวลาที่เลือก — ลองขยาย date range ออก |
| Render.com response ช้า | ปกติ — free tier spin down 15 นาที, request แรกจะช้า ~30s |
