import '../../core/api_client.dart';
import 'service_models.dart';

class ServicesRepository {
  ServicesRepository(this._api);
  final ApiClient _api;

  Future<(List<ProviderCategory>, List<Provider>)> providers({String? category}) async {
    final res = await _api.dio.get('/service/providers/', queryParameters: {
      if (category != null && category.isNotEmpty) 'category': category,
    });
    final cats = ((res.data['categories'] as List?) ?? [])
        .map((e) => ProviderCategory.fromJson(e)).toList();
    final items = ((res.data['results'] as List?) ?? [])
        .map((e) => Provider.fromJson(e)).toList();
    return (cats, items);
  }

  /// To'lov yozuvini yaratadi (pending). Keyin /payments/initiate/ bilan to'lanadi.
  Future<ServicePayment> pay({
    required String providerId,
    required int amount,
    String payerName = '',
    String period = '',
  }) async {
    final res = await _api.dio.post('/service/pay/', data: {
      'provider': providerId,
      'amount': amount,
      'payer_name': payerName,
      'period': period,
    });
    return ServicePayment.fromJson(res.data);
  }
}
