# Ish hisoboti — avtonom sessiya (≈2 soat)

**Sana:** 2026-06-21
**Diqqat markazi:** Django web + mobil REST API backend'ni professional darajaga yetkazish.

---

## ⚠️ Muhim cheklovlar (siz bilishingiz shart)

1. **Linux sandbox ishlamadi** — diskда yetarli joy bo'lmagani uchun izolyatsiya
   muhiti ishga tushmadi. Shu sababli men kodni **ishga tushira olmadim**
   (`migrate`, `test`, `runserver` bajarilmadi). Butun kod statik tahlil bilan
   yozildi va tekshirildi. **Quyidagi buyruqlarni o'zingiz ishga tushiring**
   (pastdagi "Tekshirish" bo'limiga qarang).
2. **Flutter loyihasi bu papkada yo'q** — `merged_project` ichида mobil ilova
   fayllari yo'q (ulanmagan). Shuning uchun mobil tomonга tegmadim; faqat
   backend API ustida ishladim (mobil bu API'larга keyin ulanadi).

---

## ✅ Bajarilgan ishlar

### 1. Notifications (bildirishnomalar) REST API — yakunlandi
Web tomoni avval tayyor edi; mobil API qismi qo'shildi:
- `api/notifications_serializers.py` — `NotificationSerializer` (icon, category_label),
  `MarkReadSerializer`.
- `api/notifications_views.py` — uchta endpoint:
  - `GET /api/notifications/` — ro'yxat (`limit`, `offset`, `unread=1`), `unread` soni bilan.
  - `GET /api/notifications/unread-count/` — qo'ng'iroq badge'i uchun.
  - `POST /api/notifications/read/` — `{"ids": [...]}` yoki bo'sh tana (hammasini o'qildi qiladi).
- `api/urls.py` — uchala endpoint ulandi.

### 2. Xavfsizlik: OTP / login throttling — qo'shildi
SMS-bombing va brute-force eng katta zaiflik edi. Tuzatildi:
- `api/throttles.py` — `PhoneSendThrottle`: OTP yuborishni **telefon raqami bo'yicha**
  cheklaydi (faqat IP emas) — bitta raqamga ko'p kod yuborilishining oldini oladi.
- `sdev/settings.py` — yangi rate'lar: `otp_send=5/min`, `otp_verify=10/min`, `login=10/min`.
- `api/views.py` — `RegisterView`/`ResendOTPView` → `PhoneSendThrottle`;
  `VerifyOTPView` → `otp_verify`; `LoginView` → `login` (parol brute-force himoyasi).

### 3. Ma'lumotlar yaxlitligi: poyga holatlari (race conditions) — tuzatildi
- **Delivery checkout** (`api/delivery_views.py`): tranzaksiya ichида
  `select_for_update` bilan stock qayta tekshiriladi — bir vaqtda kelgan
  buyurtmalarda **oversell** (ortiqcha sotish)ning oldi olindi.
- **Booking** (`api/booking_views.py`): venue qatori lock qilinadi —
  **double-booking** (bir slotni ikki kishi band qilishi)ning oldi olindi.

### 4. Bildirishnoma izchilligi — qo'shildi
Delivery checkout allaqachon do'kon egasiga xabar yuborardi; xuddi shu naqsh
boshqa modullarga ham qo'llandi:
- **Taksi** (`api/taxi_views.py`): `Trip` yaratilganda taksistга (hisobi bo'lsa)
  "Yangi sayohat/yetkazma" bildirishnomasi.
- **Booking** (`api/booking_views.py`): bron yaratilganда joy egasига "Yangi bron"
  bildirishnomasi (o'z joyiга bron qilsa — yuborilmaydi).

### 5. Multi-store buyurtmani bo'lish (split) — qo'shildi
Bitta savatda bir nechta do'kon mahsuloti bo'lsa, endi **har do'kon uchun
alohida buyurtma** yaratiladi (har biri o'z yetkazish narxiga ega):
- `api/delivery_views.py` (API checkout) — javob endi `{"orders": [...], "count": n}`.
- `delivery/views.py` (web checkout) — do'kon bo'yicha bo'linadi, ko'rsatiladigan
  yetkazish narxi do'kon soniga ko'paytiriladi; ko'p buyurtma bo'lsa "Buyurtmalarim"
  sahifasiga yo'naltiriladi. Oversell himoyasi (`select_for_update`) ham qo'shildi.

### 6. Avtomatlashtirilgan testlar — kengaytirildi
- `api/tests.py` — 21+ test: **notifications** (7), **auth** (OTP oqimi, login,
  throttle), **delivery** (savat, stock, checkout, multi-store split), **taxi**
  (trip + bildirishnoma), **booking** (bron, double-booking, bekor qilish).

---

## 🔍 Tekshirilgan, lekin o'zgartirish shart bo'lmagan (sifatли yozilgan)
- `sdev/settings.py` — production-ready: env bilan boshqarish, `DEBUG=False`'da
  security headerlar (HSTS, secure cookie, SSL redirect), JWT, CORS, logging (FS
  fallback bilan), Redis channel/cache opsiyasi.
- `sdev/asgi.py` + `api/ws_auth.py` — WebSocket'lar JWT bilan himoyalangan,
  `AllowedHostsOriginValidator` bilan hijacking himoyasi.
- `main/consumers.py` — real-time chat to'liq (media, reply, edit, delete,
  reaction, mention, typing, presence, read-receipt).

---

## 📋 Tekshirish (siz ishga tushiring)

Disk bo'shaганидan keyin, loyiha papkasida:

```bash
# 1. Sintaksis
python -m py_compile api/*.py sdev/settings.py

# 2. Django konfiguratsiya tekshiruvi
python manage.py check

# 3. Yangi migratsiya kerakmi?
python manage.py makemigrations --check --dry-run

# 4. Testlar
python manage.py test api
```

Kutilgan natija: `check` — "System check identified no issues",
`test api` — barcha testlar `OK`.

---

## ⚠️ DIQQAT — buzuvchi o'zgarish (Flutter uchun)
API checkout (`POST /api/checkout/`) javobi **o'zgardi**: ilgari bitta `order`
obyekti qaytardi, endi `{"orders": [...], "count": n}` qaytaradi (multi-store
split sababli). Flutter checkout ekrani shu yangi formatga moslashtirilishi kerak.

## ⏭️ Keyingi qadamlar (qolgan ishlar)
1. **Haqiqiy to'lov shlyuzi** (Payme/Click/Uzum) — hozir karta to'lovi demo.
2. **SMS shlyuzi** — hozir OTP konsolga/logga chiqadi (`api/views.py:_create_and_send_otp`).
   Productionda Eskiz/Play Mobile kabi provayder ulang.
3. **Flutter** — bildirishnoma ekrani + qo'ng'iroq badge'i va checkout javobining
   yangi formatga moslashuvi. Buning uchun mobil loyiha papkasini ulang
   (bu sessiyada papka ulanmagan edi, mobil fayllarga kira olmadim).
4. Testlarni CI'ga ulash (GitHub Actions).
