# SamCity — Mobil ilova (Flutter) yo'l xaritasi

> Maqsad: mavjud **Django super-app**ni Android + iOS uchun **Flutter** mobil ilovaga aylantirish.
> Backend (ma'lumotlar bazasi, biznes-logika) saqlanadi — unga faqat **REST API** qatlami qo'shiladi.
> Mobil interfeys Flutter'da yangidan quriladi.

---

## Arxitektura

```
┌─────────────────┐      JSON / HTTPS      ┌──────────────────────┐
│  Flutter ilova   │  ◄──────────────────►  │  Django + DRF (API)   │
│  (Android / iOS) │      JWT token         │  mavjud logika+DB     │
└─────────────────┘                         └──────────────────────┘
        ▲                                              ▲
   yangi interfeys                          o'zgarmaydi (faqat /api/ qo'shiladi)
```

- **Backend:** Django (mavjud) + Django REST Framework (yangi). Veb-sayt o'z holicha ishlayveradi.
- **Auth:** telefon + OTP (mavjud) → JWT token (mobil uchun).
- **Frontend:** Flutter (bitta kod bazasi → Android va iOS).

---

## Bosqichlar

### ✅ 0. Tayyorgarlik
- Modullar ro'yxati: e'lonlar, ish, taksi, yetkazish, booking, to'lovlar, joylar, chat, bildirishnomalar.
- MVP (birinchi ishlaydigan versiya): **Auth + E'lonlar**. Keyin modul-modul kengaytiriladi.

### 1. Backend → REST API (Django)
- `djangorestframework`, `djangorestframework-simplejwt`, `django-cors-headers`, `drf-spectacular` o'rnatish.
- `settings.py`: DRF, JWT, CORS sozlash.
- **Auth API:** `/api/auth/register/`, `/api/auth/verify-otp/`, `/api/auth/login/`, `/api/auth/refresh/`, `/api/auth/me/`.
- **Ads API:** ro'yxat + qidiruv/filtr/sort, detal, yaratish, o'z e'lonlarim, sevimlilar.
- Swagger hujjat: `/api/docs/`.

### 2. Flutter loyiha skeleti
- Paketlar: `dio` (HTTP), `flutter_riverpod` (holat), `go_router` (navigatsiya), `flutter_secure_storage` (token).
- Papka tuzilishi: `core/` (api, auth, theme), `features/<modul>/`, `shared/`.
- SamCity dizayni: emerald/teal rang, dark mode, shriftlar.

### 3. Flutter — Auth oqimi
- Kirish → OTP → token saqlash → avtomatik kirish.

### 4. Flutter — E'lonlar (MVP)
- Bosh ro'yxat → qidiruv/filtr → detal → e'lon qo'shish.

### 5. Keyingi modullar
- Yetkazish (savat), Taksi (xarita + real-time), Booking, Chat, Profil, To'lovlar.

### 6. Native imkoniyatlar
- Push (Firebase FCM), kamera/rasm yuklash, GPS/xarita, offline kesh.

### 7. Chiqarish
- Android: APK/AAB → Play Store.
- iOS: build → App Store (Mac kerak).

---

## Texnik tafsilotlar

**Stack**

| Qatlam | Texnologiya |
|---|---|
| Backend | Django + Django REST Framework |
| Auth | SimpleJWT (telefon+OTP asosida) |
| Mobil | Flutter (Dart) |
| HTTP | dio |
| Holat | Riverpod |
| Navigatsiya | go_router |
| Token saqlash | flutter_secure_storage |

**API namunasi (Ads)**

```
GET  /api/ads/?q=&category=&sort=&page=     → e'lonlar ro'yxati
GET  /api/ads/{id}/                          → bitta e'lon
POST /api/ads/                               → yangi e'lon (auth)
GET  /api/ads/mine/                          → mening e'lonlarim (auth)
POST /api/ads/{id}/favorite/                 → sevimliga qo'shish (auth)
```

---

## Eslatma
- Hozircha bulutdagi sinov muhiti (Linux shell) **disk to'liq** bo'lgani uchun kod ishga tushirib sinab ko'rilmaydi — kod yoziladi, **lokalda** `python manage.py migrate` / `runserver` va `flutter run` bilan tekshiriladi.
- Flutter ishlatish uchun: **Flutter SDK** + Android Studio (Android) / Xcode+Mac (iOS) kerak.

---

*Avtomatik yaratildi — SamCity mobil ilova rejasi.*
