import '../../core/api_client.dart';
import 'delivery_models.dart';

class DeliveryRepository {
  DeliveryRepository(this._api);
  final ApiClient _api;

  Future<List<Store>> stores({String? query}) async {
    final res = await _api.dio.get('/stores/', queryParameters: {
      if (query != null && query.isNotEmpty) 'search': query,
    });
    final results = (res.data['results'] as List?) ?? [];
    return results.map((e) => Store.fromJson(e)).toList();
  }

  Future<StoreDetail> storeDetail(String id) async {
    final res = await _api.dio.get('/stores/$id/');
    return StoreDetail.fromJson(res.data);
  }

  Future<Cart> cart() async {
    final res = await _api.dio.get('/cart/');
    return Cart.fromJson(res.data);
  }

  /// Foydalanuvchining yetkazish buyurtmalari (eng yangi oldin).
  Future<List<DeliveryOrder>> orders() async {
    final res = await _api.dio.get('/orders/');
    final results = (res.data['results'] as List?) ?? (res.data as List?) ?? [];
    return results.map((e) => DeliveryOrder.fromJson(e)).toList();
  }

  Future<DeliveryOrder> orderDetail(String id) async {
    final res = await _api.dio.get('/orders/$id/');
    return DeliveryOrder.fromJson(res.data);
  }

  // ── Egasi: do'kon va mahsulot boshqaruvi ──
  Future<(List<Map<String, dynamic>>, List<Store>)> myStores() async {
    final res = await _api.dio.get('/my/stores/');
    final cats = ((res.data['categories'] as List?) ?? [])
        .map((e) => {'id': e['id'], 'name': e['name'] ?? ''}).toList();
    final stores = ((res.data['results'] as List?) ?? [])
        .map((e) => Store.fromJson(e)).toList();
    return (cats, stores);
  }

  Future<void> createStore(Map<String, dynamic> data) async {
    await _api.dio.post('/my/stores/', data: data);
  }

  Future<void> addProduct(String storeId, Map<String, dynamic> data) async {
    await _api.dio.post('/stores/$storeId/products/', data: data);
  }

  Future<Cart> add(String productId, {int quantity = 1}) async {
    final res = await _api.dio.post('/cart/add/',
        data: {'product_id': productId, 'quantity': quantity});
    return Cart.fromJson(res.data);
  }

  Future<Cart> setQty(String productId, int quantity) async {
    final res = await _api.dio.post('/cart/set/',
        data: {'product_id': productId, 'quantity': quantity});
    return Cart.fromJson(res.data);
  }

  Future<Cart> remove(String productId) async {
    final res = await _api.dio.post('/cart/remove/', data: {'product_id': productId});
    return Cart.fromJson(res.data);
  }

  /// Savatni buyurtma(lar)ga aylantiradi. Multi-store split tufayli javob
  /// bir nechta buyurtma bo'lishi mumkin ({orders, count}).
  Future<CheckoutResult> checkout({
    required String fullName,
    required String phone,
    required String address,
    String note = '',
    String paymentMethod = 'cash',
  }) async {
    final res = await _api.dio.post('/checkout/', data: {
      'full_name': fullName,
      'phone': phone,
      'address': address,
      'note': note,
      'payment_method': paymentMethod,
    });
    return CheckoutResult.fromJson(res.data);
  }
}
