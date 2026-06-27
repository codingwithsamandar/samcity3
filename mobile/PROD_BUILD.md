# SamCity mobil — Prod build qo'llanmasi

Bu hujjat ilovani App Store / Play Store uchun tayyorlash bosqichlarini izohlaydi.
Barcha xavfsizlik va imzo sozlamalari kodga qo'shilgan — sizdan faqat kalit va
ikonka kerak.

## 1. Xavfsizlik (allaqachon sozlangan)

- **Android:** `usesCleartextTraffic` olib tashlandi. Endi `network_security_config.xml`
  prod'da **faqat HTTPS** ga ruxsat beradi; HTTP faqat lokal hostlar (10.0.2.2,
  localhost) uchun. Prod API'ngiz HTTPS bo'lishi shart.
- **iOS:** `Info.plist` da ATS yoqilgan (`NSAllowsArbitraryLoads=false`), lokal
  tarmoqqa istisno bor. Joylashuv/kamera/galereya ruxsat tavsiflari qo'shilgan.

## 2. Release imzo kaliti (Android)

```bash
keytool -genkey -v -keystore ~/samcity-release.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias samcity
```

So'ng `android/key.properties.example` ni `android/key.properties` deb nusxalab,
parol va `storeFile` yo'lini to'ldiring. (Bu fayl `.gitignore` da — git'ga tushmaydi.)

`key.properties` bo'lsa release avtomatik shu kalit bilan imzolanadi; bo'lmasa
debug kalit bilan (dev/CI buzilmaydi).

> Application ID ni `com.example.samcity` dan o'z domeningizga o'zgartiring
> (`android/app/build.gradle.kts` → `applicationId`).

## 3. Ikonka va splash

1024×1024 PNG'ni `assets/icon/icon.png` (va `icon_foreground.png`, `splash.png`) ga qo'ying:

```bash
flutter pub get
flutter pub run flutter_launcher_icons
flutter pub run flutter_native_splash:create
```

## 4. Build

```bash
# API manzilini kompilyatsiyada beramiz (prod HTTPS):
flutter build appbundle --release \
  --dart-define=API_BASE=https://api.samcity.uz/api

flutter build ipa --release \
  --dart-define=API_BASE=https://api.samcity.uz/api
```

## 5. Sifat tekshiruvi

```bash
flutter analyze        # 0 ogohlantirish bo'lishi kerak
dart format --output=none --set-exit-if-changed .
flutter test
```

## Eslatma — xato boshqaruvi

`lib/core/api_error.dart` markazlashgan: `apiErrorMessage(e)` har qanday tarmoq/
server xatosini o'zbekcha tushunarli matnga aylantiradi. Ekranlardagi
`catch` bloklarida shuni ishlating:

```dart
try { ... } catch (e) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(apiErrorMessage(e))));
}
```
