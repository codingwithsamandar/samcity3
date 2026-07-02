# SamCity — Render.com'ga deploy qilish

Loyiha Render uchun tayyor. `render.yaml` (Blueprint) quyidagilarni avtomatik yaratadi:

| Xizmat | Turi | Tavsif |
|---|---|---|
| `samcity` | Web (Docker, Daphne ASGI) | HTTP + WebSocket (chat/tracking). `entrypoint.sh`: migrate → collectstatic → daphne |
| `samcity-telegram-bot` | Worker | Telegram OTP boti (doimiy polling). ⚠️ **pulli plan talab qiladi** |
| `samcity-db` | PostgreSQL | Bepul 1GB baza (avtomatik ulanadi) |
| `samcity-redis` | Redis/Key-Value | Channels real-time layer + cache (ixtiyoriy) |

---

## 1-qadam: Kodni GitHub'ga yuklash

Repo allaqachon mavjud bo'lsa — faqat push qiling:

```bash
git add .
git commit -m "Render deploy tayyorligi + Telegram OTP"
git push
```

Yangi repo bo'lsa:
```bash
git remote add origin https://github.com/FOYDALANUVCHI/samcity.git
git branch -M main
git push -u origin main
```

> `.gitignore` `venv/`, `db.sqlite3`, `media/`, `.env` ni chiqarib tashlaydi — **maxfiy narsalar (token, parollar) yuklanmaydi**.

---

## 2-qadam: Render'da Blueprint orqali deploy

1. [render.com](https://render.com) — GitHub bilan kiring.
2. **New → Blueprint** → `samcity` repo'ni tanlang → Render `render.yaml` ni o'qiydi.
3. **Apply**. Render web + Postgres + Redis'ni yaratadi va `DJANGO_SECRET_KEY` ni avtomatik generatsiya qiladi.
4. Birinchi build ~3-5 daqiqa.

Tugagach: `https://samcity.onrender.com` (yoki Render bergan nom).

---

## 3-qadam: Qo'lda kiritiladigan env vars (Render → Environment)

Bular `render.yaml`'da **`sync: false`** — ya'ni maxfiy, blueprint'da yozilmagan, **Render panelida qo'lda** kiritiladi (`samcity → Environment → Add`):

| O'zgaruvchi | Majburiymi | Qayerdan |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram OTP uchun | @BotFather (quyida) |
| `TELEGRAM_BOT_USERNAME` | ixtiyoriy | bot username (deep-link uchun) |
| `SMS_ESKIZ_EMAIL` / `SMS_ESKIZ_PASSWORD` | SMS OTP uchun | eskiz.uz kabineti |
| `PAYME_MERCHANT_ID` / `PAYME_MERCHANT_KEY` | to'lov uchun | Payme kabineti |
| `CLICK_SERVICE_ID` / `CLICK_SECRET_KEY` | to'lov uchun | Click kabineti |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | media saqlash | Supabase/S3 |
| `SENTRY_DSN` | ixtiyoriy | sentry.io |

**Avtomatik (qo'lda tegmaysiz):** `DJANGO_SECRET_KEY` (generateValue), `POSTGRES_*` (bazadan), `REDIS_URL` (redis xizmatidan), `DJANGO_DEBUG=False`, `ALLOWED_HOSTS`, `TELEGRAM_OTP_ENABLED=True`.

> **OTP kanali:** `TELEGRAM_BOT_TOKEN` kiritilsa va raqam Telegram'ga ulangan bo'lsa — kod Telegram'da keladi; aks holda **SMS'ga qaytadi**. Ikkalasi ham bo'sh bo'lsa, tez sinov uchun `SMS_BACKEND=console` qiling — kod Render loglarida ko'rinadi.

---

## 4-qadam: Telegram OTP boti

**Token olish (@BotFather):** Telegram'da `@BotFather` → `/newbot` → nom + username → tokenni oling.

1. Tokenni `TELEGRAM_BOT_TOKEN` ga qo'ying (3-qadam) — **web va worker ikkalasida ham bir xil**.
2. Worker (`samcity-telegram-bot`) — bu Telegram polling boti. ⚠️ **Render'da Background Worker pulli plan talab qiladi** (`render.yaml`'da `plan: starter`).
   - **Bepul qolmoqchi bo'lsangiz:** `render.yaml`'dan `worker` blokini o'chiring. OTP baribbr ishlaydi:
     - Yuborish **web** xizmatidan bo'ladi (web'da ham token bor).
     - Bot faqat foydalanuvchi o'zi raqam ulashi (`/start`) uchun kerak. Buni qo'lda ham qilish mumkin: `link_telegram_demo` (Render Shell'da yoki lokalda).
3. Ishlaganini tekshirish: `https://t.me/<bot_username>` → `/start` → «📱 Raqamni ulashish».

---

## 5-qadam: Admin yaratish

**A) Avtomatik** — `render.yaml`/Environment'ga qo'shing: `DJANGO_SUPERUSER_PHONE` va `DJANGO_SUPERUSER_PASSWORD` (entrypoint.sh o'zi yaratadi).

**B) Qo'lda** (pulli planda Shell bor): Render → samcity → **Shell**:
```bash
python manage.py createsuperuser
```

`https://samcity.onrender.com/admin/` orqali kiring.

---

## Bepul tarif cheklovlari

| Narsa | Cheklov | Yechim |
|---|---|---|
| Web uxlashi | 15 daq harakatsizlikda uxlaydi (~1 daq uyg'onish) | Demo uchun normal; Starter ($7/oy) doimiy |
| Worker (Telegram bot) | **Bepul tarifda YO'Q** | Starter plan, yoki worker'ni o'chirib SMS/qo'lda-link'dan foydalaning |
| PostgreSQL | 1GB, muddati cheklangan | Muddatida yangilang yoki pulli baza |
| Media (rasm) | Disk vaqtinchalik | Supabase S3 / Cloudinary (render.yaml'da S3 sozlangan) |
| Redis | Bepul, cheklangan | Kerak bo'lmasa `worker`+`redis` blok va `REDIS_URL` ni o'chiring (in-memory ishlaydi) |

---

## Tez-tez uchraydigan xatolar

- **502 / build fail** → Render → Logs. Ko'pincha `entrypoint.sh` CRLF sababli — `.gitattributes` hal qiladi.
- **CSS yo'q / admin buzilgan** → logda `collectstatic` qatorini tekshiring (whitenoise sozlangan).
- **DisallowedHost** → `DJANGO_ALLOWED_HOSTS` da `.onrender.com` bor (render.yaml'da).
- **Login ishlamayapti** → OTP kanali sozlanmagan (3-qadam): SMS yoki Telegram token, yoki `SMS_BACKEND=console`.
- **Telegram bot 409 Conflict** → bitta token bilan ikkita poller ishlayapti (masalan lokal + Render worker). Faqat bittasini qoldiring.
