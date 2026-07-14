import '../../core/api_client.dart';
import 'taxi_models.dart' show TaxiRoute;
import 'taxist_panel_models.dart';

/// Taksi haydovchi (taksist) paneli — /api/taxi/me/ endpointlari.
class TaxistPanelRepository {
  TaxistPanelRepository(this._api);
  final ApiClient _api;

  Future<TaxistPanel> panel() async {
    final res = await _api.dio.get('/taxi/me/');
    return TaxistPanel.fromJson(res.data as Map<String, dynamic>);
  }

  Future<TaxistProfile> register({
    required String fullName,
    required String phone,
    String carModel = '',
    String region = '',
  }) async {
    final res = await _api.dio.post('/taxi/me/register/', data: {
      'full_name': fullName,
      'phone': phone,
      'car_model': carModel,
      if (region.isNotEmpty) 'region': region,
    });
    return TaxistProfile.fromJson(res.data as Map<String, dynamic>);
  }

  Future<TaxistProfile> updateProfile(Map<String, dynamic> data) async {
    final res = await _api.dio.patch('/taxi/me/', data: data);
    return TaxistProfile.fromJson(res.data as Map<String, dynamic>);
  }

  /// Onlayn/oflayn holatini almashtiradi; yangi holatni qaytaradi.
  Future<bool> toggleOnline() async {
    final res = await _api.dio.post('/taxi/me/online/');
    return res.data['is_online'] == true;
  }

  Future<TaxiRoute> addRoute({
    required String pointA,
    required String pointB,
    required int passengerPrice,
    int? deliveryPrice,
    String note = '',
  }) async {
    final res = await _api.dio.post('/taxi/me/routes/', data: {
      'point_a': pointA,
      'point_b': pointB,
      'passenger_price': passengerPrice,
      if (deliveryPrice != null) 'delivery_price': deliveryPrice,
      if (note.isNotEmpty) 'note': note,
    });
    return TaxiRoute.fromJson(res.data as Map<String, dynamic>);
  }

  Future<void> deleteRoute(String routeId) async {
    await _api.dio.delete('/taxi/me/routes/$routeId/');
  }
}
