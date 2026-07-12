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

  /// Markaziy katalog — do'kon egasi mahsulot tanlashi uchun.
  /// search: nom/brend/kategoriya nomi; filtrlar: categoryId, brand (aniq), unit.
  /// Sahifalangan (DRF, 20 tadan): natija bilan birga keyingi sahifa bor-yo'qligi
  /// qaytadi — picker shu bayroq bo'yicha davomini yuklaydi.
  Future<(List<CatalogProduct>, bool hasMore)> catalog(
      {String? search, Object? categoryId, String? brand, String? unit,
      int page = 1}) async {
    final res = await _api.dio.get('/catalog/', queryParameters: {
      if (search != null && search.isNotEmpty) 'search': search,
      if (categoryId != null) 'category': categoryId,
      if (brand != null && brand.isNotEmpty) 'brand': brand,
      if (unit != null && unit.isNotEmpty) 'unit': unit,
      if (page > 1) 'page': page,
    });
    final data = res.data;
    final results = (data is Map ? data['results'] as List? : data as List?) ?? [];
    final hasMore = data is Map && data['next'] != null;
    return (results.map((e) => CatalogProduct.fromJson(e)).toList(), hasMore);
  }

  Future<void> updateProduct(
      String storeId, String productId, Map<String, dynamic> data) async {
    await _api.dio.patch('/stores/$storeId/products/$productId/', data: data);
  }

  Future<void> updateStore(String storeId, Map<String, dynamic> data) async {
    await _api.dio.patch('/my/stores/$storeId/', data: data);
  }

  /// Do'kon yangiliklari tasmasi (sahifalangan, eng yangisi oldin).
  Future<List<StoreUpdateItem>> storeUpdates(String storeId) async {
    final res = await _api.dio.get('/stores/$storeId/updates/');
    final results = (res.data['results'] as List?) ?? [];
    return results.map((e) => StoreUpdateItem.fromJson(e)).toList();
  }

  /// Do'kon yangiliklaridan xabardor bo'lishni yoqadi/o'chiradi.
  Future<bool> toggleSubscription(String storeId) async {
    final res = await _api.dio.post('/stores/$storeId/subscribe/');
    return res.data['subscribed'] ?? false;
  }

  Future<void> postAnnouncement(String storeId, String text) async {
    await _api.dio.post('/stores/$storeId/announce/', data: {'text': text});
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

  // ── E'lon saqlash (savatning e'lonlar bo'limi) ──
  Future<Cart> addAdToCart(String adId) async {
    final res = await _api.dio.post('/cart/ad/', data: {'ad_id': adId});
    return Cart.fromJson(res.data);
  }

  Future<Cart> removeAdFromCart(String adId) async {
    final res = await _api.dio.delete('/cart/ad/', data: {'ad_id': adId});
    return Cart.fromJson(res.data);
  }

  // ── Saqlangan (nomli) savatlar ──
  Future<Cart> createCart(String name) async {
    final res = await _api.dio.post('/cart/carts/', data: {'name': name});
    return Cart.fromJson(res.data);
  }

  Future<Cart> renameCart(String cartId, String name) async {
    final res = await _api.dio.patch('/cart/carts/$cartId/', data: {'name': name});
    return Cart.fromJson(res.data);
  }

  Future<void> deleteCart(String cartId) async {
    await _api.dio.delete('/cart/carts/$cartId/');
  }

  Future<Cart> activateCart(String cartId) async {
    final res = await _api.dio.post('/cart/carts/$cartId/activate/');
    return Cart.fromJson(res.data);
  }

  /// Savatni buyurtma(lar)ga aylantiradi. Multi-store split tufayli javob
  /// bir nechta buyurtma bo'lishi mumkin ({orders, count}).
  Future<CheckoutResult> checkout({
    required String fullName,
    required String phone,
    String address = '',
    String note = '',
    String paymentMethod = 'cash',
    DateTime? pickupAt,
  }) async {
    final res = await _api.dio.post('/checkout/', data: {
      'full_name': fullName,
      'phone': phone,
      'address': address,
      'note': note,
      'payment_method': paymentMethod,
      if (pickupAt != null) 'pickup_at': pickupAt.toIso8601String(),
    });
    return CheckoutResult.fromJson(res.data);
  }

  /// Mijoz pickup buyurtmani qo'lga olganini tasdiqlaydi (yakuniy holat).
  Future<DeliveryOrder> confirmPickup(String orderId) async {
    final res = await _api.dio.post('/orders/$orderId/confirm-pickup/');
    return DeliveryOrder.fromJson(res.data);
  }

  /// Do'kon egasi: o'z do'konlariga kelgan buyurtmalar (?fulfillment=pickup).
  Future<List<DeliveryOrder>> storeOrders({String? fulfillment}) async {
    final res = await _api.dio.get('/my/orders/', queryParameters: {
      if (fulfillment != null) 'fulfillment': fulfillment,
    });
    final results = (res.data['results'] as List?) ?? (res.data as List?) ?? [];
    return results.map((e) => DeliveryOrder.fromJson(e)).toList();
  }

  /// Do'kon egasi buyurtma holatini o'zgartiradi (preparing/ready/...).
  Future<DeliveryOrder> setStoreOrderStatus(String orderId, String status) async {
    final res = await _api.dio.post('/my/orders/$orderId/status/', data: {'status': status});
    return DeliveryOrder.fromJson(res.data);
  }
}
