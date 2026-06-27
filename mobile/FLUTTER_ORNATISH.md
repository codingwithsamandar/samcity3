# Flutter o'rnatish va APK yasash (Windows)

APK yasash uchun **Flutter SDK** + **Android SDK** kerak. Bu bir martalik
o'rnatish (~30–40 daqiqa, ~8 GB joy kerak — diskда joy borligini tekshiring).

---

## A YO'L — Kompyuterda o'rnatish (tavsiya etiladi)

### 1. Android Studio o'rnatish (Android SDK shu bilan keladi)
- Yuklab oling: https://developer.android.com/studio
- O'rnatib, bir marta ishga tushiring → "More Actions" → **SDK Manager** →
  "Android SDK Command-line Tools" ni belgilab o'rnating.

### 2. Flutter SDK o'rnatish
- Yuklab oling: https://docs.flutter.dev/get-started/install/windows/mobile
- ZIP'ni `C:\flutter` ga chiqaring (extract).
- **PATH**ga qo'shing:
  - Windows qidiruvда "environment variables" → "Edit the system environment
    variables" → "Environment Variables" → "Path" → "New" → `C:\flutter\bin`.
- Yangi CMD oynasini oching va tekshiring:
  ```
  flutter doctor
  ```

### 3. Litsenziyalarni qabul qiling
```
flutter doctor --android-licenses
```
Hammasiga `y` deb javob bering.

### 4. `flutter doctor` ni qayta ishga tushiring
Quyidagilar yashil ✓ bo'lishi kerak:
- Flutter
- Android toolchain

(Boshqa qatorlar — VS Code, Chrome — APK uchun shart emas.)

### 5. APK yasang
`mobile` papkasidagi **`build_apk.bat`** ni bosing — yoki:
```
cd C:\Users\user\Desktop\merged_project\mobile
flutter pub get
flutter build apk --release --dart-define=API_BASE=http://SIZNING_IP:8000/api
```

Tayyor APK: `mobile\build\app\outputs\flutter-apk\app-release.apk`

---

## B YO'L — Bulutda yasash (kompyuterga hech narsa o'rnatmasdan)
Agar diskда joy yetmasa yoki o'rnatish qiyin bo'lsa, APK'ni **GitHub'da bepul**
yasash mumkin. Buning uchun:
1. Loyihani GitHub'ga yuklaysiz (men `build-apk.yml` workflow faylini
   tayyorlab beraman).
2. GitHub o'zi APK yasaydi va yuklab olish uchun beradi.

> Bu yo'lni xohlasangiz, ayting — GitHub Actions faylini sozlab beraman.
> (Eslatma: bulutda yasalgan APK ham telefon WiFi orqali kompyuterdagi
> serverga ulanadi, shuning uchun IP/WiFi sharti baribir saqlanadi — agar
> backend internetga joylashtirilmagan bo'lsa.)

---

## Tez yordam
- `flutter doctor` natijasini menga to'liq yuborsangiz, qayerda muammo
  borligini aniqlab, aniq qadamlarni aytaman.
- "flutter is not recognized" → PATH to'g'ri qo'shilmagan (2-qadam).
- "Android SDK not found" / "cmdline-tools missing" → 1-qadam (SDK Manager).
