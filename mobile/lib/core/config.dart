/// Ilova sozlamalari (API manzili va h.k.).
class AppConfig {
  /// Backend API bazaviy manzili.
  ///
  /// - Android emulyator: kompyuterdagi localhost = 10.0.2.2
  /// - iOS simulyator: 127.0.0.1
  /// - Haqiqiy qurilma: kompyuteringizning lokal IP'si (masalan 192.168.x.x)
  ///
  /// `--dart-define=API_BASE=...` orqali lokal dev uchun override qilish mumkin.
  /// Masalan: `--dart-define=API_BASE=http://10.0.2.2:8000/api` (Android emulator)
  static const String apiBase = String.fromEnvironment(
    'API_BASE',
    defaultValue: 'https://samcity.onrender.com/api',
  );

  /// WebSocket bazaviy manzili (apiBase'dan hosil qilinadi).
  /// http://host:8000/api → ws://host:8000
  static String get wsBase {
    var b = apiBase;
    if (b.endsWith('/api')) b = b.substring(0, b.length - 4);
    if (b.startsWith('https')) return b.replaceFirst('https', 'wss');
    return b.replaceFirst('http', 'ws');
  }
}
