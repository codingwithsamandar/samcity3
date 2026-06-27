import '../../core/api_client.dart';

/// To'lov URL'lari (Payme / Click) — initiate API javobi.
class PaymentLinks {
  final String targetType;
  final String targetId;
  final int amount;
  final String paymeUrl;
  final String clickUrl;

  PaymentLinks({
    required this.targetType,
    required this.targetId,
    required this.amount,
    required this.paymeUrl,
    required this.clickUrl,
  });

  factory PaymentLinks.fromJson(Map<String, dynamic> j) => PaymentLinks(
        targetType: j['target_type'] ?? '',
        targetId: j['target_id']?.toString() ?? '',
        amount: (j['amount'] is num) ? (j['amount'] as num).toInt() : 0,
        paymeUrl: j['payme_url'] ?? '',
        clickUrl: j['click_url'] ?? '',
      );
}

class PaymentRepository {
  PaymentRepository(this._api);
  final ApiClient _api;

  /// Berilgan obyekt uchun to'lov URL'larini oladi.
  /// [targetType]: order | trip | booking | service
  Future<PaymentLinks> initiate(String targetType, String targetId) async {
    final res = await _api.dio.post('/payments/initiate/', data: {
      'target_type': targetType,
      'target_id': targetId,
    });
    return PaymentLinks.fromJson(res.data);
  }
}
