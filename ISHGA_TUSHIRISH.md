# SamCity — ilovani ishga tushirish qo'llanmasi (Windows)

Ilova 2 qismdan iborat: **Backend** (Django serveri) va **Flutter mobil ilova**.
Avval backendni ishga tushiring, keyin Flutterни.

---

## 1-QISM: Backend (Django serveri)

### 1.1. Terminal ochish
- `merged_project` papkasini oching.
- Manzil satriga `cmd` yozib Enter bosing (yoki papkada Shift+o'ng tugma → "Open in Terminal").

### 1.2. Kutubxonalarni o'rnatish (faqat birinchi marta)
```
pip install -r requirements.txt
```

### 1.3. Bazani tayyorlash (faqat birinchi marta)
```
python manage.py migrate
```

### 1.4. (Ixtiyoriy) Demo ma'lumot va admin
```
python manage.py demo_data
python manage.py createsuperuser
```

### 1.5. Serverni ishga tushirish
```
python manage.py runserver 0.0.0.0:8000
```
✅ Tekshirish: brauzerда `http://127.0.0.1:8000/api/docs/` ochilsa — API ishlayapti.

> ⚠️ Bu terminalni YOPMANG — server ishlab turishi kerak. Flutter uchun YANGI terminal oching.

---

## 2-QISM: Flutter mobil ilova

### 2.1. Flutter o'rnatilganmi tekshirish
Yangi terminalда:
```
flutter --version
```
- Agar versiya chiqsa → 2.3 ga o'ting.
- Agar "flutter topilmadi" desa → avval Flutter SDK o'rnatish kerak:
  1. https://docs.flutter.dev/get-started/install/windows dan Flutter SDK yuklang.
  2. Android Studio'ni o'rnating (Android SDK + emulyator uchun).
  3. `flutter doctor` buyrug'i bilan hammasi joyidaligini tekshiring.

### 2.2. Telefon yoki emulyator tayyorlash
- **Emulyator:** Android Studio → "Device Manager" → virtual qurilma yarating va ishga tushiring.
- **Haqiqiy telefon:** USB bilan ulang, telefonда "USB debugging" yoqilgan bo'lsin.

Ulangan qurilmani ko'rish:
```
flutter devices
```

### 2.3. Ilova papkasini tayyorlash (faqat birinchi marta)
```
cd mobile
flutter create .
flutter pub get
```
> `flutter create .` — android/ios papkalarini hosil qiladi (yozilgan kod saqlanadi).

### 2.4. Ilovani ishga tushirish
```
flutter run
```

---

## Qaysi API manzilini ishlatish kerak?

Flutter ilova backendga ulanishi kerak. Holatga qarab:

| Holat | Buyruq |
|---|---|
| Android emulyator (odatiy) | `flutter run` (default `10.0.2.2:8000`) |
| iOS simulyator (Mac) | `flutter run --dart-define=API_BASE=http://127.0.0.1:8000/api` |
| Haqiqiy telefon (Wi-Fi) | `flutter run --dart-define=API_BASE=http://<KOMPYUTER_IP>:8000/api` |

**Kompyuter IP'sini bilish:** terminalда `ipconfig` → "IPv4 Address" (masalan `192.168.1.50`).
Telefon va kompyuter bir Wi-Fi'da bo'lishi shart.

---

## Birinchi ishlatish (test)
1. Ilova ochiladi → "Ro'yxatdan o'tish" → telefon + ism + parol.
2. OTP kod **backend terminalida** chiqadi: `DEBUG: OTP for +998... is 123456`.
3. Shu kodni kiriting → ilovaga kirasiz.

---

## Tez-tez uchraydigan xatolar
- **"Connection refused" / ma'lumot kelmaydi** → backend ishlayaptimi tekshiring; API_BASE to'g'rimi (emulyatorда `10.0.2.2`, telefonда kompyuter IP).
- **`flutter` topilmadi** → Flutter SDK PATH'ga qo'shilmagan; `flutter doctor` bilan tekshiring.
- **Rasm ko'rinmaydi** → backend `runserver` da `0.0.0.0:8000` bilan ishga tushganmi tekshiring.
