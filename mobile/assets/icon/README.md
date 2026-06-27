# App ikonka va splash (`assets/icon/`)

> ✅ **Build buzilmaydi:** `flutter pub get` va `flutter build apk/ipa` shu
> fayllarsiz ham ishlaydi (standart Flutter ikonkasi ishlatiladi). Bu fayllar
> faqat **maxsus ikonka/splash generatorini** ishga tushirganda kerak.

## Kerakli PNG fayllar

| Fayl | O'lcham | Tavsif |
|------|---------|--------|
| `icon.png` | 1024×1024 | Asosiy app ikonkasi |
| `icon_foreground.png` | 1024×1024 | Android adaptiv ikonka (markaziy logo, shaffof fon) |
| `splash.png` | ~1152×1152 | Ochilish ekrani logosi |

`icon.svg` — shu papkadagi manba. Uni PNG ga aylantiring:

```bash
# Variant A — onlayn: svg→png (1024x1024) konverter
# Variant B — Inkscape:
inkscape icon.svg -w 1024 -h 1024 -o icon.png
# Variant C — ImageMagick:
magick -background none icon.svg -resize 1024x1024 icon.png
```

## Generatorlarni ishga tushirish

PNG fayllar tayyor bo'lgach, `mobile/` papkasidan:

```bash
flutter pub get
flutter pub run flutter_launcher_icons
flutter pub run flutter_native_splash:create
```

Sozlamalar `pubspec.yaml` da (`flutter_launcher_icons:` va
`flutter_native_splash:` bo'limlari) allaqachon mavjud.
