/// Modul flaglari — backend'dagi `settings.TAXI_ENABLED` bilan mos.
///
/// Taksi moduli ARXIVLANGAN: foydalanuvchi uchun tab, ekran, marshrut va
/// menyu yozuvlari ko'rinmaydi. Kod joyida qoladi.
///
/// Qayta yoqish (backend'da ham `TAXI_ENABLED=True` bo'lishi shart):
///   flutter run  --dart-define=TAXI_ENABLED=true
///   flutter build apk --release --dart-define=TAXI_ENABLED=true
const bool kTaxiEnabled = bool.fromEnvironment('TAXI_ENABLED');
