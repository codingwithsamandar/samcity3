/// E'lon modellari (API javobiga mos).
class AdListItem {
  final String id;
  final String title;
  final int? price;
  final String priceType;
  final String category;
  final String categoryDisplay;
  final String location;
  final bool isBoosted;
  final int views;
  final String? cover;
  final DateTime? createdAt;

  AdListItem({
    required this.id,
    required this.title,
    this.price,
    required this.priceType,
    required this.category,
    required this.categoryDisplay,
    required this.location,
    required this.isBoosted,
    required this.views,
    this.cover,
    this.createdAt,
  });

  factory AdListItem.fromJson(Map<String, dynamic> j) => AdListItem(
        id: j['id'].toString(),
        title: j['title'] ?? '',
        price: j['price'],
        priceType: j['price_type'] ?? 'fixed',
        category: j['category'] ?? '',
        categoryDisplay: j['category_display'] ?? '',
        location: j['location'] ?? '',
        isBoosted: j['is_boosted'] ?? false,
        views: j['views'] ?? 0,
        cover: j['cover'],
        createdAt: DateTime.tryParse(j['created_at'] ?? ''),
      );

  String get priceLabel {
    if (priceType == 'free') return 'Bepul';
    if (priceType == 'negotiable') return 'Kelishiladi';
    if (price == null) return '—';
    return '${_money(price!)} so\'m';
  }

  static String _money(int v) {
    final s = v.toString();
    final buf = StringBuffer();
    for (int i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) buf.write(' ');
      buf.write(s[i]);
    }
    return buf.toString();
  }
}

class AdDetail {
  final String id;
  final String title;
  final String description;
  final int? price;
  final String priceType;
  final String categoryDisplay;
  final String location;
  final int views;
  final List<String> images;
  final String? contactPhone;
  final String ownerName;
  final String? ownerAvatar;

  AdDetail({
    required this.id,
    required this.title,
    required this.description,
    this.price,
    required this.priceType,
    required this.categoryDisplay,
    required this.location,
    required this.views,
    required this.images,
    this.contactPhone,
    required this.ownerName,
    this.ownerAvatar,
  });

  factory AdDetail.fromJson(Map<String, dynamic> j) => AdDetail(
        id: j['id'].toString(),
        title: j['title'] ?? '',
        description: j['description'] ?? '',
        price: j['price'],
        priceType: j['price_type'] ?? 'fixed',
        categoryDisplay: j['category_display'] ?? '',
        location: j['location'] ?? '',
        views: j['views'] ?? 0,
        images: ((j['images'] as List?) ?? [])
            .map((e) => e['image'].toString())
            .toList(),
        contactPhone: j['contact_phone'],
        ownerName: (j['user']?['name']?.toString().isNotEmpty ?? false)
            ? j['user']['name']
            : (j['user']?['phone'] ?? ''),
        ownerAvatar: j['user']?['avatar'],
      );

  String get priceLabel {
    if (priceType == 'free') return 'Bepul';
    if (priceType == 'negotiable') return 'Kelishiladi';
    if (price == null) return '—';
    return '${AdListItem._money(price!)} so\'m';
  }
}
