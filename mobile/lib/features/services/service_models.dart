class Provider {
  final String id;
  final String name;
  final String category;
  final String categoryLabel;
  final String description;
  final String address;
  final String phone;
  final String? logo;
  final int amount; // 0 = foydalanuvchi summani kiritadi
  final bool hasFixedAmount;

  Provider({
    required this.id,
    required this.name,
    required this.category,
    required this.categoryLabel,
    required this.description,
    required this.address,
    required this.phone,
    this.logo,
    required this.amount,
    required this.hasFixedAmount,
  });

  factory Provider.fromJson(Map<String, dynamic> j) => Provider(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        category: j['category'] ?? '',
        categoryLabel: j['category_label'] ?? '',
        description: j['description'] ?? '',
        address: j['address'] ?? '',
        phone: j['phone'] ?? '',
        logo: (j['logo'] is String && (j['logo'] as String).isNotEmpty) ? j['logo'] : null,
        amount: (j['amount'] is num) ? (j['amount'] as num).toInt() : 0,
        hasFixedAmount: j['has_fixed_amount'] ?? false,
      );
}

class ProviderCategory {
  final String key;
  final String label;
  ProviderCategory({required this.key, required this.label});
  factory ProviderCategory.fromJson(Map<String, dynamic> j) =>
      ProviderCategory(key: j['key'] ?? '', label: j['label'] ?? '');
}

class ServicePayment {
  final String id;
  final String providerName;
  final int amount;
  final String statusLabel;

  ServicePayment({
    required this.id,
    required this.providerName,
    required this.amount,
    required this.statusLabel,
  });

  factory ServicePayment.fromJson(Map<String, dynamic> j) => ServicePayment(
        id: j['id'].toString(),
        providerName: j['provider_name'] ?? '',
        amount: (j['amount'] is num) ? (j['amount'] as num).toInt() : 0,
        statusLabel: j['status_label'] ?? '',
      );
}
