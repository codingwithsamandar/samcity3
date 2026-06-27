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
  final String? logo;
  final String? category;
  final int productCount;

  Store({
    required this.id,
    required this.name,
    required this.description,
    required this.address,
    required this.phone,
    this.logo,
    this.category,
    required this.productCount,
  });

  factory Store.fromJson(Map<String, dynamic> j) => Store(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        description: j['description'] ?? '',
        address: j['address'] ?? '',
        phone: j['phone'] ?? '',
        logo: j['logo'],
        category: j['category'],
        productCount: j['product_count'] ?? 0,
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

  Product({
    required this.id,
    required this.name,
    required this.description,
    required this.price,
    required this.stock,
    required this.isAvailable,
    this.cover,
    this.images = const [],
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
      );

  String get priceLabel => "${money(price)} so'm";
}

class StoreDetail {
  final Store store;
  final List<Product> products;
  StoreDetail({required this.store, required this.products});

  factory StoreDetail.fromJson(Map<String, dynamic> j) => StoreDetail(
        store: Store.fromJson(j),
        products: ((j['products'] as List?) ?? [])
            .map((e) => Product.fromJson(e))
            .toList(),
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
    required this.subtotal,
    required this.deliveryFee,
    required this.total,
    required this.paymentMethod,
    required this.paymentStatus,
    this.createdAt,
    this.items = const [],
  });

  bool get isPaid => paymentStatus == 'paid';

  factory DeliveryOrder.fromJson(Map<String, dynamic> j) => DeliveryOrder(
        id: j['id'].toString(),
        status: j['status'] ?? 'pending',
        statusDisplay: j['status_display'] ?? '',
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
