# SamCity — Flutter mobil ilova

Bu papka SamCity mobil ilovasi (Android + iOS) kodini saqlaydi.
Backend — yuqoridagi Django loyihasi (`/api/` REST endpoint'lari).

## Tuzilma

```
mobile/
├── pubspec.yaml              # paketlar
└── lib/
    ├── main.dart             # kirish nuqtasi
    ├── core/
    │   ├── config.dart       # API manzili
    │   ├── theme.dart        # emerald/dark dizayn
    │   ├── api_client.dart   # dio + JWT interceptor (avto-refresh)
    │   ├── token_storage.dart# tokenni xavfsiz saqlash
    │   ├── router.dart       # go_router marshrutlari
    │   ├── providers.dart    # riverpod provayderlar
    │   └── auth/             # user modeli + auth repozitoriy + controller
    └── features/
        ├── auth/             # login + OTP ekranlari
        └── ads/              # e'lonlar: model, repo, ro'yxat, detal
```

## ⚠️ Birinchi marta ishga tushirish

Bu papkada hozircha faqat `lib/` va `pubspec.yaml` bor. Platforma fayllari
(`android/`, `ios/`) Flutter tomonidan yaratiladi:

```bash
cd mobile
flutter create .          # mavjud lib/ va pubspec.yaml saqlanadi, android/ios qo'shiladi
flutter pub get
```

## Backendni ishga tushirish (boshqa terminalda)

```bash
# loyiha ildizida
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

API hujjat: http://127.0.0.1:8000/api/docs/

## Ilovani ishga tushirish

```bash
# Android emulyator (localhost = 10.0.2.2, default)
flutter run

# Haqiqiy telefon yoki boshqa manzil uchun:
flutter run --dart-define=API_BASE=http://192.168.1.50:8000/api
```

| Holat | API_BASE |
|---|---|
| Android emulyator | `http://10.0.2.2:8000/api` (default) |
| iOS simulyator | `http://127.0.0.1:8000/api` |
| Haqiqiy qurilma | `http://<kompyuter-IP>:8000/api` |

## MVP holati

✅ Kirish / Ro'yxatdan o'tish (telefon + parol)
✅ OTP tasdiqlash (DEBUG'da kod konsolda chiqadi)
✅ JWT token saqlash + avtomatik yangilash
✅ Pastki navigatsiya: E'lonlar · Taksi · Yetkazish · Chat · Profil
✅ E'lonlar ro'yxati + qidiruv + detal
✅ Taksi: taksistlar → marshrutlar → buyurtma (yo'lovchi/dostavka) → sayohatlarim
✅ Yetkazish: do'konlar → mahsulotlar → savat (ikona) → checkout (naqd)
✅ Chat: mahalla xonalari → xabarlar (admin tasdig'i bilan yozish), 4s polling
✅ Booking: joylar (tur filtri) → detal → sana tanlab bron → bronlarim (bekor qilish)
✅ Profil: ma'lumot + Joylar/Bronlarim/Sayohatlarim + chiqish

## Keyingi qadamlar
- E'lon qo'shish (rasm yuklash bilan)
- Checkout / taksi to'lovida karta (demo) formasi
- Chat real-time (WebSocket — hozir polling), rasm/ovoz yuborish
- Taksi real-time tracking (WebSocket), xarita
- Push bildirishnoma (Firebase FCM), offline kesh
