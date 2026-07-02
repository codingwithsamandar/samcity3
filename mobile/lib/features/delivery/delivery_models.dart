String money(int v) {
  final s = v.toString();
  final buf = StringBuffer();
  for (int i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0) buf.write(' ');
    buf.write(s[i]);
  }
  return buf.toString();
}

class Store {
  final String id;
  final String name;
  final String description;
  final String address;
  final String phone;
  final String workingHours;
  final String? logo;
  final String? category;
  final int productCount;
  final bool cartEnabled;

  Store({
    required this.id,
    required this.name,
    required this.description,
    required this.address,
    required this.phone,
    this.workingHours = '',
    this.logo,
    this.category,
    required this.productCount,
    this.cartEnabled = false,
  });

  factory Store.fromJson(Map<String, dynamic> j) => Store(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        description: j['description'] ?? '',
        address: j['address'] ?? '',
        phone: j['phone'] ?? '',
        workingHours: j['working_hours'] ?? '',
        logo: j['logo'],
        category: j['category'],
        productCount: j['product_count'] ?? 0,
        cartEnabled: j['cart_enabled'] ?? false,
      );
}

class StoreUpdateItem {
  final String id;
  final String updateType;
  final String updateTypeDisplay;
  final String text;
  final String? image;
  final String? productName;
  final int? oldPrice;
  final int? newPrice;
  final DateTime? createdAt;

  StoreUpdateItem({
    required this.id,
    required this.updateType,
    required this.updateTypeDisplay,
    required this.text,
    this.image,
    this.productName,
    this.oldPrice,
    this.newPrice,
    this.createdAt,
  });

  factory StoreUpdateItem.fromJson(Map<String, dynamic> j) => StoreUpdateItem(
        id: j['id'].toString(),
        updateType: j['update_type'] ?? '',
        updateTypeDisplay: j['update_type_display'] ?? '',
        text: j['text'] ?? '',
        image: j['image'],
        productName: j['product_name'],
        oldPrice: (j['old_price'] is num) ? (j['old_price'] as num).toInt() : null,
        newPrice: (j['new_price'] is num) ? (j['new_price'] as num).toInt() : null,
        createdAt: DateTime.tryParse(j['created_at'] ?? ''),
      );
}

class Product {
  final String id;
  final String name;
  final String description;
  final int price;
  final int stock;
  final bool isAvailable;
  final String? cover;
  final List<String> images;
  final DateTime? restockAt;
  final bool pickup;

  Product({
    required this.id,
    required this.name,
    required this.description,
    required this.price,
    required this.stock,
    required this.isAvailable,
    this.cover,
    this.images = const [],
    this.restockAt,
    this.pickup = false,
  });

  factory Product.fromJson(Map<String, dynamic> j) => Product(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        description: j['description'] ?? '',
        price: (j['price'] is num) ? (j['price'] as num).toInt() : 0,
        stock: j['stock'] ?? 0,
        isAvailable: j['is_available'] ?? true,
        cover: j['cover'],
        images: ((j['images'] as List?) ?? [])
            .map((e) => e['image'].toString())
            .toList(),
        restockAt: DateTime.tryParse(j['restock_at'] ?? ''),
        pickup: j['pickup'] ?? false,
      );

  String get priceLabel => "${money(price)} so'm";

  /// "2 kun 4 soat 12 daqiqa qoldi" — yoki muddat o'tgan bo'lsa null.
  String? restockCountdownLabel() {
    if (restockAt == null) return null;
    final remaining = restockAt!.difference(DateTime.now());
    if (remaining.isNegative) return null;
    final d = remaining.inDays;
    final h = remaining.inHours % 24;
    final m = remaining.inMinutes % 60;
    final parts = <String>[];
    if (d > 0) parts.add('$d kun');
    if (h > 0 || d > 0) parts.add('$h soat');
    parts.add('$m daqiqa');
    return '${parts.join(' ')} qoldi';
  }
}

class StoreDetail {
  final Store store;
  final List<Product> products;
  final String ownerBio;
  final String? ownerPhoto;
  final List<String> gallery;
  final List<StoreUpdateItem> updates;
  final bool subscribed;

  StoreDetail({
    required this.store,
    required this.products,
    this.ownerBio = '',
    this.ownerPhoto,
    this.gallery = const [],
    this.updates = const [],
    this.subscribed = false,
  });

  factory StoreDetail.fromJson(Map<String, dynamic> j) => StoreDetail(
        store: Store.fromJson(j),
        products: ((j['products'] as List?) ?? [])
            .map((e) => Product.fromJson(e))
            .toList(),
        ownerBio: j['owner_bio'] ?? '',
        ownerPhoto: j['owner_photo'],
        gallery: ((j['gallery'] as List?) ?? [])
            .map((e) => e['image'].toString())
            .toList(),
        updates: ((j['updates'] as List?) ?? [])
            .map((e) => StoreUpdateItem.fromJson(e))
            .toList(),
        subscribed: j['subscribed'] ?? false,
      );
}

class CartItem {
  final String id;
  final Product product;
  final int quantity;
  final int lineTotal;
  CartItem({
    required this.id,
    required this.product,
    required this.quantity,
    required this.lineTotal,
  });

  factory CartItem.fromJson(Map<String, dynamic> j) => CartItem(
        id: j['id'].toString(),
        product: Product.fromJson(j['product']),
        quantity: j['quantity'] ?? 1,
        lineTotal: (j['line_total'] is num) ? (j['line_total'] as num).toInt() : 0,
      );
}

class Cart {
  final List<CartItem> items;
  final int totalQuantity;
  final int subtotal;
  Cart({required this.items, required this.totalQuantity, required this.subtotal});

  factory Cart.fromJson(Map<String, dynamic> j) => Cart(
        items: ((j['items'] as List?) ?? [])
            .map((e) => CartItem.fromJson(e))
            .toList(),
        totalQuantity: j['total_quantity'] ?? 0,
        subtotal: (j['subtotal'] is num) ? (j['subtotal'] as num).toInt() : 0,
      );

  static Cart empty() => Cart(items: [], totalQuantity: 0, subtotal: 0);
}

class OrderLine {
  final String productName;
  final String storeName;
  final int price;
  final int quantity;
  final int lineTotal;

  OrderLine({
    required this.productName,
    required this.storeName,
    required this.price,
    required this.quantity,
    required this.lineTotal,
  });

  factory OrderLine.fromJson(Map<String, dynamic> j) => OrderLine(
        productName: j['product_name'] ?? '',
        storeName: j['store_name'] ?? '',
        price: (j['price'] is num) ? (j['price'] as num).toInt() : 0,
        quantity: j['quantity'] ?? 1,
        lineTotal: (j['line_total'] is num) ? (j['line_total'] as num).toInt() : 0,
      );
}

class DeliveryOrder {
  final String id;
  final String status;
  final String statusDisplay;
  final String progressLabel;
  final String fulfillmentType;
  final bool canConfirmPickup;
  final int subtotal;
  final int deliveryFee;
  final int total;
  final String paymentMethod;
  final String paymentStatus;
  final DateTime? createdAt;
  final List<OrderLine> items;

  DeliveryOrder({
    required this.id,
    required this.status,
    required this.statusDisplay,
    this.progressLabel = '',
    this.fulfillmentType = 'delivery',
    this.canConfirmPickup = false,
    required this.subtotal,
    required this.deliveryFee,
    required this.total,
    required this.paymentMethod,
    required this.paymentStatus,
    this.createdAt,
    this.items = const [],
  });

  bool get isPaid => paymentStatus == 'paid';
  bool get isPickup => fulfillmentType == 'pickup';
  String get label => progressLabel.isNotEmpty ? progressLabel : statusDisplay;

  factory DeliveryOrder.fromJson(Map<String, dynamic> j) => DeliveryOrder(
        id: j['id'].toString(),
        status: j['status'] ?? 'pending',
        statusDisplay: j['status_display'] ?? '',
        progressLabel: j['progress_label'] ?? '',
        fulfillmentType: j['fulfillment_type'] ?? 'delivery',
        canConfirmPickup: j['can_confirm_pickup'] ?? false,
        subtotal: (j['subtotal'] is num) ? (j['subtotal'] as num).toInt() : 0,
        deliveryFee: (j['delivery_fee'] is num) ? (j['delivery_fee'] as num).toInt() : 0,
        total: (j['total'] is num) ? (j['total'] as num).toInt() : 0,
        paymentMethod: j['payment_method'] ?? 'card',
        paymentStatus: j['payment_status'] ?? 'unpaid',
        createdAt: DateTime.tryParse(j['created_at'] ?? ''),
        items: ((j['items'] as List?) ?? [])
            .map((e) => OrderLine.fromJson(e))
            .toList(),
      );
}

/// Checkout natijasi — multi-store split tufayli bir nechta buyurtma bo'lishi
/// mumkin. Backend javobi: {"orders": [...], "count": n}.
class CheckoutResult {
  final List<DeliveryOrder> orders;
  final int count;
  CheckoutResult({required this.orders, required this.count});

  factory CheckoutResult.fromJson(Map<String, dynamic> j) => CheckoutResult(
        orders: ((j['orders'] as List?) ?? [])
            .map((e) => DeliveryOrder.fromJson(e))
            .toList(),
        count: j['count'] ?? 0,
      );

  int get totalAmount => orders.fold(0, (sum, o) => sum + o.total);
}
