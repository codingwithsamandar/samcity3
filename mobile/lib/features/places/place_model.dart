class Place {
  final String id;
  final String name;
  final String category;
  final String categoryLabel;
  final String icon;
  final String color;
  final double lat;
  final double lng;
  final String address;
  final String phone;
  final String hours;
  final String description;
  final String? image;

  Place({
    required this.id,
    required this.name,
    required this.category,
    required this.categoryLabel,
    required this.icon,
    required this.color,
    required this.lat,
    required this.lng,
    required this.address,
    required this.phone,
    required this.hours,
    required this.description,
    this.image,
  });

  factory Place.fromJson(Map<String, dynamic> j) => Place(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        category: j['category'] ?? '',
        categoryLabel: j['category_label'] ?? '',
        icon: j['icon'] ?? '📍',
        color: j['color'] ?? '#0ea371',
        lat: (j['latitude'] is num) ? (j['latitude'] as num).toDouble() : 0,
        lng: (j['longitude'] is num) ? (j['longitude'] as num).toDouble() : 0,
        address: j['address'] ?? '',
        phone: j['phone'] ?? '',
        hours: j['working_hours'] ?? '',
        description: j['description'] ?? '',
        image: (j['image'] is String && (j['image'] as String).isNotEmpty) ? j['image'] : null,
      );
}

class PlaceCategory {
  final String key;
  final String label;
  PlaceCategory({required this.key, required this.label});
  factory PlaceCategory.fromJson(Map<String, dynamic> j) =>
      PlaceCategory(key: j['key'] ?? '', label: j['label'] ?? '');
}

class PlacesData {
  final List<PlaceCategory> categories;
  final List<Place> places;
  PlacesData({required this.categories, required this.places});
}
