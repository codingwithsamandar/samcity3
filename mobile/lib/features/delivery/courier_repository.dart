import '../../core/api_client.dart';
import 'courier_models.dart';
import 'delivery_models.dart';

/// Kuryer (yetkazib beruvchi) paneli — /api/courier/ endpointlari.
class CourierRepository {
  CourierRepository(this._api);
  final ApiClient _api;

  Future<CourierDashboard> dashboard() async {
    final res = await _api.dio.get('/courier/');
    return CourierDashboard.fromJson(res.data as Map<String, dynamic>);
  }

  Future<CourierProfile> register({
    required String fullName,
    required String phone,
    String vehicleType = 'moto',
    String vehicleNumber = '',
  }) async {
    final res = await _api.dio.post('/courier/register/', data: {
      'full_name': fullName,
      'phone': phone,
      'vehicle_type': vehicleType,
      'vehicle_number': vehicleNumber,
    });
    return CourierProfile.fromJson(res.data as Map<String, dynamic>);
  }

  Future<CourierProfile> updateProfile(Map<String, dynamic> data) async {
    final res = await _api.dio.patch('/courier/profile/', data: data);
    return CourierProfile.fromJson(res.data as Map<String, dynamic>);
  }

  /// Bo'sh/band holatini almashtiradi; yangi holatni qaytaradi.
  Future<bool> toggleAvailable() async {
    final res = await _api.dio.post('/courier/available/');
    return res.data['is_available'] == true;
  }

  Future<DeliveryOrder> accept(String orderId) async {
    final res = await _api.dio.post('/courier/orders/$orderId/accept/');
    return DeliveryOrder.fromJson(res.data as Map<String, dynamic>);
  }

  Future<DeliveryOrder> release(String orderId) async {
    final res = await _api.dio.post('/courier/orders/$orderId/release/');
    return DeliveryOrder.fromJson(res.data as Map<String, dynamic>);
  }

  /// status: picked_up / on_the_way / delivered
  Future<DeliveryOrder> setStatus(String orderId, String status) async {
    final res = await _api.dio.post('/courier/orders/$orderId/status/',
        data: {'status': status});
    return DeliveryOrder.fromJson(res.data as Map<String, dynamic>);
  }
}
