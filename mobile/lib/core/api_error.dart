import 'package:dio/dio.dart';

/// Markazlashgan API xatolarini foydalanuvchiga tushunarli (o'zbekcha) matnga
/// aylantiradi. Har ekranda `catch (e) { showError(apiErrorMessage(e)); }`
/// ko'rinishida ishlatiladi — texnik stack trace o'rniga toza xabar chiqadi.
String apiErrorMessage(Object error) {
  if (error is DioException) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'Server javob bermayapti. Internetni tekshirib, qayta urinib ko\'ring.';
      case DioExceptionType.connectionError:
        return 'Internetga ulanib bo\'lmadi. Aloqani tekshiring.';
      case DioExceptionType.badCertificate:
        return 'Xavfsiz ulanishda muammo (sertifikat).';
      case DioExceptionType.cancel:
        return 'So\'rov bekor qilindi.';
      case DioExceptionType.badResponse:
        return _fromResponse(error.response);
      case DioExceptionType.unknown:
        return 'Noma\'lum xatolik. Qayta urinib ko\'ring.';
    }
  }
  return 'Xatolik yuz berdi. Qayta urinib ko\'ring.';
}

/// HTTP status + server javobidan eng aniq xabarni ajratadi.
String _fromResponse(Response? resp) {
  final code = resp?.statusCode ?? 0;
  // Server bergan matnli xatoni afzal ko'ramiz (DRF: {detail|error|message}).
  final data = resp?.data;
  if (data is Map) {
    for (final key in ['detail', 'error', 'message']) {
      final v = data[key];
      if (v is String && v.trim().isNotEmpty) return v;
    }
    // Maydon-bo'yicha validatsiya xatolari (DRF): birinchisini ko'rsatamiz.
    for (final v in data.values) {
      if (v is List && v.isNotEmpty && v.first is String) return v.first as String;
      if (v is String && v.trim().isNotEmpty) return v;
    }
  }
  switch (code) {
    case 400:
      return 'Ma\'lumotlar noto\'g\'ri. Tekshirib qaytadan kiriting.';
    case 401:
      return 'Sessiya tugadi. Iltimos, qaytadan kiring.';
    case 403:
      return 'Bu amal uchun ruxsatingiz yo\'q.';
    case 404:
      return 'Topilmadi.';
    case 409:
      return 'Bu vaqt allaqachon band. Boshqa vaqt tanlang.';
    case 429:
      return 'Juda ko\'p urinish. Birozdan so\'ng qayta urinib ko\'ring.';
    case 500:
    case 502:
    case 503:
      return 'Serverda vaqtincha muammo. Birozdan so\'ng urinib ko\'ring.';
  }
  return 'Xatolik ($code). Qayta urinib ko\'ring.';
}
