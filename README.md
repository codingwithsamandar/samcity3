# SamCity — shahar super-ilovasi

Django (ASGI/Channels + DRF) backend va Flutter mobil ilova. Bitta platformada:
e'lonlar, yetkazib berish, taksi, joy bron qilish (xizmat/usta/slot), mahalla
chat, bildirishnomalar, xarita, ish/rezyume, kommunal to'lovlar va onlayn to'lov
(Payme/Click).

```
merged_project/
├── sdev/            # Django sozlamalari (settings, asgi, urls)
├── main/ delivery/ taxi/ payments/ booking/ notifications/ places/ api/   # 8 app
├── mobile/          # Flutter ilova
├── requirements.txt
├── Dockerfile  docker-compose.yml  nginx.conf  entrypoint.sh
└── .env.example
```

---

## 1. Backend — lokal ishga tushirish

```bash
# 1) Klon
git clone <repo-url> samcity && cd samcity

# 2) Virtual muhit
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3) Bog'liqliklar
pip install -r requirements.txt

# 4) Sozlama (lokal uchun ixtiyoriy — default SQLite + DEBUG=True)
cp .env.example .env        # va qiymatlarni to'ldiring (yoki lokalda bo'sh qoldiring)

# 5) Migratsiya + demo ma'lumot
python manage.py migrate
python manage.py seed_demo_full     # demo: foydalanuvchi, e'lon, do'kon, joy...
python manage.py seed_booking       # bron: xizmat/usta
python manage.py seed_places        # xarita nuqtalari

# 6) Server (WebSocket bilan — ASGI)
python manage.py runserver          # http://127.0.0.1:8000
```

> OTP kodi SMS o'rniga **server konsoliga** chiqadi: `DEBUG: OTP for +998... is 123456`.

### Testlar
```bash
python manage.py test           # barcha app testlari
python manage.py check --deploy # production tekshiruvi
```

### API hujjati
- OpenAPI sxema: `http://127.0.0.1:8000/api/schema/`
- Swagger UI:   `http://127.0.0.1:8000/api/docs/`
- Liveness: `/api/health/` · Readiness (DB+Redis): `/api/ready/`

---

## 2. Muhit o'zgaruvchilari (`.env`)

Barcha sozlamalar env orqali (`.env.example` ga qarang). Asosiylari:

| O'zgaruvchi | Tavsif |
|-------------|--------|
| `DJANGO_SECRET_KEY` | Maxfiy kalit (production'da SHART) |
| `DJANGO_DEBUG` | Production'da `False` |
| `DJANGO_ALLOWED_HOSTS` | `domen.uz,www.domen.uz` |
| `CSRF_TRUSTED_ORIGINS` | `https://domen.uz` |
| `POSTGRES_*` | PostgreSQL (yo'q bo'lsa SQLite) |
| `REDIS_URL` | Channels + cache (yo'q bo'lsa in-memory) |
| `CORS_ALLOWED_ORIGINS` | Mobil/web klient domeni |
| `PAYME_*`, `CLICK_*` | To'lov shlyuzi kalitlari |
| `SENTRY_DSN` | Xato kuzatuvi (ixtiyoriy) |

---

## 3. Production deploy (Docker)

To'liq stack: **daphne (ASGI) + PostgreSQL 16 + Redis 7 + nginx**.

```bash
cp .env.example .env        # production qiymatlari bilan to'ldiring (DEBUG=False!)
docker compose up -d --build
```

- `web` — daphne ASGI (WebSocket: chat/taksi/yetkazish jonli ishlaydi).
- `nginx` — `/static/`, `/media/` to'g'ridan; `/ws/` upgrade; qolganini proxy.
- Migratsiya + collectstatic `entrypoint.sh` orqали avtomatik.

**HTTPS:** `nginx.conf` ichidagi "PRODUCTION HTTPS" blokini yoqing va
`./certs/` ichiga `fullchain.pem` + `privkey.pem` qo'ying (masalan certbot bilan).

Healthcheck'lar Docker'da: web → `/api/health/`, db → `pg_isready`, redis → `ping`.

---

## 4. Mobil ilova (Flutter)

```bash
cd mobile
flutter pub get

# Lokal sinov (Android emulyator backend'i = 10.0.2.2):
flutter run

# Brauzerda sinov (web):
flutter run -d chrome --dart-define=API_BASE=http://127.0.0.1:8000/api

# Release APK (production API bilan):
flutter build apk --release --dart-define=API_BASE=https://domen.uz/api
# → mobile/build/app/outputs/flutter-apk/app-release.apk
```

`API_BASE` `--dart-define` orqali beriladi (default lokal `10.0.2.2`).
Production HTTPS bo'lsa cleartext kerak emas. Sifat: `flutter analyze`.

---

## 5. Toza klon (muhim)

Repoga ilgari xato bilan `venv/`, `mobile/build/`, `mobile/.dart_tool/` kabi
katta/maxfiy fayllar tushgan bo'lsa, ularni olib tashlash uchun
**`GIT_CLEANUP.md`** ga qarang. Yangi `.gitignore` bularni endi kuzatmaydi.

Toza klondan keyin faqat:
```bash
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cd mobile && flutter pub get
```
yetarli — `venv/` va `build/` repoда bo'lmaydi, har bir ishchi o'zi yaratadi.
