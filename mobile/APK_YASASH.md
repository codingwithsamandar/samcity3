# 📱 SamCity APK — telefonda ochish qo'llanmasi

## Talablar (bir martalik)
- **Flutter SDK** o'rnatilgan bo'lishi kerak. Tekshirish: terminalda `flutter doctor`.
  Agar yo'q bo'lsa: https://docs.flutter.dev/get-started/install/windows
- Android telefoningiz va kompyuter **bir xil WiFi** tarmog'ida.

## Eng oson yo'l (skript bilan)
1. `mobile` papkasidagi **`build_apk.bat`** faylini ikki marta bosing.
2. So'raganda kompyuter **IP manzilini** kiriting (qanday topish — pastda).
3. Skript APK yasaydi. Tayyor fayl:
   `mobile\build\app\outputs\flutter-apk\app-release.apk`
4. Shu faylni telefoningizga ko'chiring (USB yoki Telegram) va o'rnating
   ("Noma'lum manbalar"ga ruxsat berishingiz kerak bo'lishi mumkin).

## Kompyuter IP manzilini topish
Terminalда (CMD) yozing:
```
ipconfig
```
**"IPv4 Address"** qatoridagi raqamni oling (masalan `192.168.1.5`).

## Serverni ishga tushirish (ilova ulanishi uchun shart)
Telefon kompyuterdagi backendga ulanadi, shuning uchun server **shu IP'da**
ochiq bo'lishi kerak:
```
cd C:\Users\user\Desktop\merged_project
python manage.py runserver 0.0.0.0:8000
```
> `0.0.0.0` — muhim: telefon tarmoq orqali ulana olishi uchun.
> Windows Firewall so'rasa — "Allow access" bosing.

## Qo'lda yasash (skriptsiz)
```
cd C:\Users\user\Desktop\merged_project\mobile
flutter pub get
flutter build apk --release --dart-define=API_BASE=http://SIZNING_IP:8000/api
```
`SIZNING_IP` o'rniga `ipconfig` dan olgan IP'ni qo'ying.

## Tez-tez uchraydigan muammolar
- **Ilova ochiladi, lekin ma'lumot yuklanmaydi** → server ishlayotganini
  (`runserver 0.0.0.0:8000`), telefon va PC bir WiFi'da ekanini, IP to'g'ri
  ekanini tekshiring. Firewall'ni ham ko'ring.
- **"flutter topilmadi"** → Flutter SDK o'rnatilmagan yoki PATH'da yo'q.
- **OTP kodi kelmaydi** → SMS shlyuzi hali ulanmagan; kod **server konsoliga**
  chiqadi (`DEBUG: OTP for ... is 123456`) — o'shani kiriting.
- **APK o'rnatilmaydi** → Sozlamalar → Xavfsizlik → "Noma'lum manbalar"ga ruxsat.

## Eslatma
- Bu **debug/sinov** uchun. Play Store uchun imzolangan (signed) APK/AAB
  alohida tayyorlanadi.
- Hozir HTTP (shifrlanmagan) ishlatiladi (lokal sinov uchun ruxsat berilgan).
  Production'da HTTPS domeni kerak bo'ladi.
