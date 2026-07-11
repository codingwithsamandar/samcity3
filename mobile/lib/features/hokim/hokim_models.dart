// Hokim paneli (tuman e'loni) — mobil modellar.

class DistrictAnnouncement {
  final String id;
  final String title;
  final String text;
  final String? image;
  final int recipientsCount;
  final DateTime? createdAt;

  DistrictAnnouncement({
    required this.id,
    required this.title,
    required this.text,
    this.image,
    this.recipientsCount = 0,
    this.createdAt,
  });

  factory DistrictAnnouncement.fromJson(Map<String, dynamic> j) => DistrictAnnouncement(
        id: j['id'].toString(),
        title: j['title'] ?? '',
        text: j['text'] ?? '',
        image: j['image'],
        recipientsCount: j['recipients_count'] ?? 0,
        createdAt: DateTime.tryParse(j['created_at'] ?? ''),
      );
}

class District {
  final String id;
  final String name;
  final String description;
  final String headName;
  final String headPhone;
  final int residentsCount;
  final int mahallasCount;

  District({
    required this.id,
    required this.name,
    this.description = '',
    this.headName = '',
    this.headPhone = '',
    this.residentsCount = 0,
    this.mahallasCount = 0,
  });

  factory District.fromJson(Map<String, dynamic> j) => District(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        description: j['description'] ?? '',
        headName: j['head_name'] ?? '',
        headPhone: j['head_phone'] ?? '',
        residentsCount: j['residents_count'] ?? 0,
        mahallasCount: j['mahallas_count'] ?? 0,
      );
}

/// Panelning bitta tuman bloki: tuman + uning e'lonlari.
class HokimDistrict {
  final District district;
  final List<DistrictAnnouncement> announcements;

  HokimDistrict({required this.district, required this.announcements});

  factory HokimDistrict.fromJson(Map<String, dynamic> j) => HokimDistrict(
        district: District.fromJson(j['district'] ?? {}),
        announcements: ((j['announcements'] as List?) ?? [])
            .map((e) => DistrictAnnouncement.fromJson(e))
            .toList(),
      );
}
