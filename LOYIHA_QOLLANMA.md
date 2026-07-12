# SamCity — Loyiha qo'llanmasi (ChatGPT uchun kontekst)

> Bu faylni ChatGPT'ga to'liq nusxalab tashlang. Undan keyin loyiha haqida
> savol bering — u butun tuzilmani, texnologiyalarni va mantiqni tushunadi.

---

## 0. ChatGPT'ga beriladigan kirish matni (shu qatorni birinchi yozing)

> "Men **SamCity** nomli loyiha ustida ishlayapman — bu O'zbekiston shaharlari
> uchun mo'ljallangan super-app (mahalla + yetkazib berish + taksi + bron +
> to'lovlar). Backend — Django (ASGI/daphne), mobil ilova — Flutter. Quyida
> loyiha to'liq tavsifi. Shu kontekst asosida savollarimga javob ber."

Keyin shu faylning qolgan qismini yopishtiring.

---

## 1. Loyiha nima?

**SamCity** — bitta ilovada bir nechta shahar xizmatini birlashtirgan super-app:

- **Mahalla/hokimlik** — e'lonlar, shikoyatlar (murojaatlar), so'rovnomalar (poll), hokim paneli, tuman e'lonlari.
- **Yetkazib berish (delivery)** — mahalla do'konlari katalogi, mahsulotlar, savat, checkout, buyurtma kuzatuvi, do'kon egasi paneli, do'kon bilan chat.
- **Taksi** — taksi xizmatlari, taksistlar, marshrutlar, safar (trip) va real-time kuzatuv.
- **Bron (booking)** — to'yxona/joylar bronlash, xizmatlar, xodimlar, no-show jarima.
- **Joylar (places)** — xaritada joylar, sharhlar, sevimlilar.
- **To'lovlar (payments)** — Payme va Click integratsiyasi, xizmat to'lovlari.
- **Bildirishnomalar** — real-time (WebSocket) + FCM push.
- **Ish e'lonlari** — vakansiya va rezyume.
- **Chat** — foydalanuvchilararo va do'kon bilan chat (WebSocket).

Sayt **3 tilda**: o'zbek (asosiy), rus, ingliz. Vaqt mintaqasi: `Asia/Tashkent`.

---

## 2. Texnologiyalar (stack)

**Backend**
- Python 3.12, **Django 5.2**
- **ASGI / daphne** (WebSocket uchun — gunicorn emas)
- **Django Channels 4** + **Redis** (channel layer, real-time)
- **Django REST Framework** + **SimpleJWT** (mobil API autentifikatsiya)
- **drf-spectacular** (OpenAPI/Swagger hujjat)
- **PostgreSQL 16** (production), SQLite (faqat lokal dev)
- **WhiteNoise** (statik fayllar), **django-jazzmin** (admin panel UI)
- **corsheaders**, **django-filter**

**Mobil**
- **Flutter** ilova (`mobile/` papkasida), backend'ga REST API + WebSocket orqali ulanadi.

**Infratuzilma / deploy**
- **Docker** (multi-stage, non-root), **docker-compose**: web + postgres + redis + nginx
- **nginx** reverse proxy (static/media, WebSocket upgrade, gzip, HTTPS)
- Media: local disk / **Cloudinary** / **AWS S3 (Supabase mos)** — env orqali tanlanadi
- Monitoring: **Sentry** (ixtiyoriy)

**Tashqi xizmatlar**
- SMS: **Eskiz.uz** yoki **Playmobile** (OTP uchun)
- Telegram bot (OTP'ni SMS o'rniga Telegram orqali yuborish — demo/dev)
- To'lov: **Payme**, **Click** (webhook'lar bilan)
- Push: **Firebase FCM** (ixtiyoriy)

---

## 3. Loyiha tuzilmasi (papkalar)

```
merged_project/
├── sdev/                  # Django loyiha yadrosi (settings, urls, asgi, wsgi)
│   ├── settings.py        # Barcha sozlama (env orqali boshqariladi)
│   ├── urls.py            # Asosiy URL router
│   └── asgi.py            # ASGI kirish nuqtasi (Channels + HTTP)
├── main/                  # Asosiy app: User, e'lonlar, mahalla, chat, poll, jobs
├── delivery/              # Yetkazib berish: Store, Product, Cart, Order, driver
├── taxi/                  # Taksi: TaxiService, Taxist, Route, Trip, Payment
├── booking/               # Bron: Venue, VenueService, VenueStaff, VenueBooking
├── places/                # Xarita joylari: Place, PlaceReview
├── payments/              # To'lov: Provider, Transaction, ServicePayment (Payme/Click)
├── notifications/         # Bildirishnomalar (WebSocket + FCM)
├── sms/                   # SMS backend abstraksiyasi (eskiz/playmobile/console)
├── telegrambot/           # Telegram OTP boti (TelegramLink)
├── api/                   # Mobil REST API (barcha app'lar uchun serializer + view)
├── mobile/                # Flutter ilova (alohida loyiha)
├── locale/                # Tarjimalar (uz/ru/en)
├── Dockerfile             # Backend image (multi-stage)
├── docker-compose.yml     # web + db + redis + nginx
├── entrypoint.sh          # migrate → collectstatic → daphne
├── nginx.conf             # reverse proxy
├── requirements.txt       # Python bog'liqliklar
├── .env / .env.example / .env.production   # muhit o'zgaruvchilari
└── DEPLOY.md              # Serverga joylash qo'llanmasi (o'zbekcha)
```

---

## 4. Django app'lari va vazifalari

| App | Vazifasi | Asosiy modellar (taxminan) |
|-----|----------|----------------------------|
| **main** | User (maxsus model), e'lonlar (Ad), mahalla/tuman, so'rovnoma, chat, ish e'lonlari | `User`, `Ad`, `District`, `Neighborhood`, `Poll`, `ChatRoom`, `JobAd`, `ResumeAd` |
| **delivery** | Do'kon katalogi, savat, buyurtma, haydovchi | `Store`, `Product`, `Cart`, `Order`, `OrderItem`, `DeliveryDriver`, `DriverLocation` |
| **taxi** | Taksi xizmati, safar, real-time joylashuv | `TaxiService`, `Taxist`, `Route`, `Car`, `Trip`, `Payment` |
| **booking** | Joy/to'yxona bronlash | `Venue`, `VenueService`, `VenueStaff`, `VenueBooking` |
| **places** | Xaritadagi joylar | `Place`, `PlaceReview`, `PlaceFavorite` |
| **payments** | To'lov provayderlari va tranzaksiyalar | `Provider`, `Transaction`, `ServicePayment` |
| **notifications** | Bildirishnomalar | `Notification`, device token'lar |
| **sms** | SMS yuborish abstraksiyasi | (backend'lar: eskiz/playmobile/console) |
| **telegrambot** | Telegram orqali OTP | `TelegramLink` |
| **api** | Yuqoridagilarning hammasi uchun mobil REST API | (serializer va view'lar) |

> **Muhim:** `AUTH_USER_MODEL = 'main.User'` — maxsus foydalanuvchi modeli.
> Foydalanuvchi **telefon raqami** bilan ro'yxatdan o'tadi (username emas).

---

## 5. Autentifikatsiya oqimi (muhim)

1. Foydalanuvchi **telefon raqami** kiritadi → `POST /api/auth/register/`.
2. Server **OTP kod** yuboradi (SMS yoki Telegram orqali).
3. `POST /api/auth/verify-otp/` bilan kod tasdiqlanadi.
4. Server **JWT** qaytaradi (access ~60 daqiqa, refresh ~30 kun).
5. Mobil ilova har so'rovda `Authorization: Bearer <access>` yuboradi.
6. Access tugasa `POST /api/auth/refresh/` bilan yangilanadi.

OTP kanali `SMS_BACKEND` bilan tanlanadi: `eskiz` | `playmobile` | `console` (dev).
`console` — haqiqiy SMS yubormaydi, kodni logga yozadi (test/dev uchun).

---

## 6. URL tuzilmasi

**Web (server-rendered, Django templates):**
```
/                → main (bosh sahifa, e'lonlar, mahalla)
/delivery/       → do'konlar, buyurtma
/taxi/           → taksi
/payments/       → to'lovlar
/booking/        → bron
/notifications/  → bildirishnomalar
/map/            → joylar (xarita)
/admin/          → admin panel (Jazzmin)
/accounts/       → login/logout
```

**Mobil REST API (`/api/` prefiksi):**
```
/api/auth/register|verify-otp|resend-otp|login|refresh|me
/api/ads/                    (ViewSet — e'lonlar)
/api/stores/ /api/orders/    (delivery)
/api/cart/... /api/checkout/
/api/taxi/services|taxists|trips
/api/booking/venues|bookings
/api/chat/rooms/...
/api/mahalla/... /api/hokim/...
/api/notifications/...
/api/payments/initiate/
/api/community/polls|help
/api/jobs/ /api/resumes/
/api/places/
/api/health/ /api/ready/     (health-check)
/api/schema/ /api/docs/       (OpenAPI / Swagger)
```

**WebSocket (Channels, `/ws/` prefiksi):** chat, taksi kuzatuvi, delivery kuzatuvi, bildirishnomalar.

---

## 7. Real-time (WebSocket)

- **Django Channels** + **Redis channel layer** (`REDIS_URL` o'rnatilganda).
- nginx `/ws/` so'rovlarini daphne'ga upgrade qiladi (uzoq ulanish: 3600s timeout).
- Ishlatiladi: chat xabarlari, taksi haydovchi joylashuvi, buyurtma statusi, bildirishnomalar.
- `REDIS_URL` bo'lmasa — `InMemoryChannelLayer` (faqat bitta jarayon, dev uchun).

---

## 8. To'lovlar

- **Payme** va **Click** webhook'lari bilan integratsiya (`payments/` app).
- Webhook xavfsizligi: `atomic + select_for_update` (qator qulfi) — parallel
  so'rovda ikki marta to'lashning oldi olingan.
- Merchant kalitlari env orqali; bo'sh bo'lsa webhook **autentifikatsiyadan
  o'tmay xavfsiz rad etadi**.

---

## 9. Muhit o'zgaruvchilari (env)

Ustuvorlik: haqiqiy environment > `.env` fayl (settings.py `setdefault` bilan yuklaydi).

**Majburiy (production):**
| O'zgaruvchi | Tavsif |
|-------------|--------|
| `DJANGO_DEBUG` | `False` (production) |
| `DJANGO_SECRET_KEY` | uzun tasodifiy kalit (dev kalitni ishlatmang!) |
| `DJANGO_ALLOWED_HOSTS` | `domen.uz,www.domen.uz` |
| `CSRF_TRUSTED_ORIGINS` | `https://domen.uz,...` |
| `POSTGRES_DB/USER/PASSWORD` | PostgreSQL (yoki `DATABASE_URL`) |
| `REDIS_URL` | real-time uchun (compose'da avtomatik) |
| `SMS_ESKIZ_EMAIL/PASSWORD` | OTP uchun — **bo'lmasa login ishlamaydi** |

**Ixtiyoriy:** `PAYME_*`, `CLICK_*`, `SENTRY_DSN`, `TELEGRAM_BOT_TOKEN`,
`CLOUDINARY_*` / `AWS_*` (media), `FIREBASE_CREDENTIALS_FILE` (push),
`SECURE_SSL_REDIRECT`, `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS`.

Fayllar: `.env` (lokal dev), `.env.example` (namuna), `.env.production` (prod shablon).

---

## 10. Lokal ishga tushirish

```bash
# 1) Virtual muhit
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt

# 2) Baza (dev — SQLite avtomatik)
python manage.py migrate
python manage.py createsuperuser

# 3) Ishga tushirish (ASGI)
python manage.py runserver       # yoki: daphne sdev.asgi:application

# 4) Testlar
python manage.py test            # 177 test
```

Dev'da `.env` da `DJANGO_DEBUG=True`, `SMS_BACKEND=console` (kod logga chiqadi).

---

## 11. Production'ga joylash (Docker)

```bash
cp .env.production .env      # va qiymatlarni to'ldiring
docker compose up -d --build # migrate + collectstatic + daphne avtomatik
```

Stack: **web (daphne) + postgres + redis + nginx**. HTTPS uchun Let's Encrypt
sertifikat olib, `nginx.conf` dagi 443 blokini yoqib, `SECURE_SSL_REDIRECT=True`
qilinadi. Batafsil — `DEPLOY.md`.

Tekshiruv:
```bash
docker compose exec web python manage.py check --deploy
docker compose exec web python manage.py test
```

---

## 12. Xavfsizlik holati (joriy)

- `DEBUG=False` da: HSTS, secure cookie, `SECURE_SSL_REDIRECT`, `X_FRAME_OPTIONS=DENY`,
  `SECURE_CONTENT_TYPE_NOSNIFF` avtomatik yoqiladi.
- DRF **throttling**: anon 60/min, user 300/min, OTP 5/min, login 10/min, checkout 20/min.
- Sirlar kodda emas — hammasi env orqali.
- `check --deploy` da chiqadigan ~100 ogohlantirish — asosan **drf-spectacular**
  (API hujjat) warninglari; runtime'ga ta'sir qilmaydi. Xavfsizlik warninglari
  faqat lokal `DEBUG=True` da chiqadi, prod'da yo'qoladi.

---

## 13. Tez-tez beriladigan savollar uchun eslatma (ChatGPT'ga)

- Loyiha **monorepo**: bitta papkada Django backend + Flutter mobil.
- Server **ASGI** (daphne), chunki WebSocket bor — WSGI/gunicorn yolg'iz yetmaydi.
- Foydalanuvchi **telefon + OTP** bilan kiradi, username yo'q.
- Ba'zi modellar `UUID` primary key ishlatadi (Order, poll, murojaat).
- Til: kod izohlar va UI matnlari **o'zbekcha**.
```
