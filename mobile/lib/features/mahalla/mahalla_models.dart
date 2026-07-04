// Mahalla bo'limi — mobil modellar.

class Neighborhood {
  final String id;
  final String name;
  final String description;
  final int? population;
  final String headName;
  final String headPhone;
  final String color;
  final List<double>? centroid;

  Neighborhood({
    required this.id,
    required this.name,
    this.description = '',
    this.population,
    this.headName = '',
    this.headPhone = '',
    this.color = '#3551d1',
    this.centroid,
  });

  factory Neighborhood.fromJson(Map<String, dynamic> j) => Neighborhood(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        description: j['description'] ?? '',
        population: j['population'],
        headName: j['head_name'] ?? '',
        headPhone: j['head_phone'] ?? '',
        color: j['color'] ?? '#3551d1',
        centroid: (j['centroid'] is List && (j['centroid'] as List).length == 2)
            ? [(j['centroid'][0] as num).toDouble(), (j['centroid'][1] as num).toDouble()]
            : null,
      );
}

class Announcement {
  final String id;
  final String title;
  final String text;
  final String? image;
  final DateTime? createdAt;

  Announcement({required this.id, required this.title, required this.text, this.image, this.createdAt});

  factory Announcement.fromJson(Map<String, dynamic> j) => Announcement(
        id: j['id'].toString(),
        title: j['title'] ?? '',
        text: j['text'] ?? '',
        image: j['image'],
        createdAt: DateTime.tryParse(j['created_at'] ?? ''),
      );
}

class MahallaPlace {
  final String id;
  final String name;
  final String category;
  final String categoryLabel;
  final String icon;
  final String address;
  final String url;
  final double? lat;
  final double? lng;

  MahallaPlace({
    required this.id,
    required this.name,
    this.category = '',
    required this.categoryLabel,
    required this.icon,
    required this.address,
    required this.url,
    this.lat,
    this.lng,
  });

  static double? _d(dynamic v) => v is num ? v.toDouble() : null;

  factory MahallaPlace.fromJson(Map<String, dynamic> j) => MahallaPlace(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        category: j['category'] ?? '',
        categoryLabel: j['category_label'] ?? '',
        icon: j['icon'] ?? '📍',
        address: j['address'] ?? '',
        url: j['url'] ?? '',
        lat: _d(j['lat']),
        lng: _d(j['lng']),
      );
}

class PlaceGroup {
  final String key;
  final String label;
  final List<MahallaPlace> items;
  PlaceGroup({required this.key, required this.label, required this.items});

  String get icon => items.isNotEmpty ? items.first.icon : '📍';

  factory PlaceGroup.fromJson(Map<String, dynamic> j) => PlaceGroup(
        key: j['key'] ?? '',
        label: j['label'] ?? '',
        items: ((j['items'] as List?) ?? []).map((e) => MahallaPlace.fromJson(e)).toList(),
      );
}

class Complaint {
  final String id;
  final String category;
  final String categoryDisplay;
  final String title;
  final String text;
  final String? image;
  final String status;
  final String statusDisplay;
  final String response;
  final String author;
  final DateTime? createdAt;

  Complaint({
    required this.id,
    required this.category,
    required this.categoryDisplay,
    required this.title,
    required this.text,
    this.image,
    required this.status,
    required this.statusDisplay,
    this.response = '',
    this.author = '',
    this.createdAt,
  });

  factory Complaint.fromJson(Map<String, dynamic> j) => Complaint(
        id: j['id'].toString(),
        category: j['category'] ?? 'other',
        categoryDisplay: j['category_display'] ?? '',
        title: j['title'] ?? '',
        text: j['text'] ?? '',
        image: j['image'],
        status: j['status'] ?? 'submitted',
        statusDisplay: j['status_display'] ?? '',
        response: j['response'] ?? '',
        author: j['author'] ?? '',
        createdAt: DateTime.tryParse(j['created_at'] ?? ''),
      );
}

class MahallaDetail {
  final Neighborhood neighborhood;
  final bool isAdmin;
  final List<Announcement> announcements;
  final List<MahallaPlace> stores;
  final List<PlaceGroup> placeGroups;

  MahallaDetail({
    required this.neighborhood,
    required this.isAdmin,
    required this.announcements,
    required this.stores,
    required this.placeGroups,
  });

  factory MahallaDetail.fromJson(Map<String, dynamic> j) => MahallaDetail(
        neighborhood: Neighborhood.fromJson(j['neighborhood'] ?? {}),
        isAdmin: j['is_admin'] ?? false,
        announcements: ((j['announcements'] as List?) ?? [])
            .map((e) => Announcement.fromJson(e)).toList(),
        stores: ((j['stores'] as List?) ?? []).map((e) => MahallaPlace.fromJson(e)).toList(),
        placeGroups: ((j['place_groups'] as List?) ?? [])
            .map((e) => PlaceGroup.fromJson(e)).toList(),
      );
}
