/// Foydalanuvchi modeli (API /auth/me/ va login javobidan).
class AppUser {
  final String id;
  final String phone;
  final String name;
  final String? avatar;
  final String role;
  final double rating;
  final bool isHokim; // tuman hokimi (yoki staff) — "Hokim paneli" kirish nuqtasi uchun
  final String gender; // '', 'male', 'female'
  final String? birthDate; // 'YYYY-MM-DD'

  AppUser({
    required this.id,
    required this.phone,
    required this.name,
    this.avatar,
    required this.role,
    required this.rating,
    this.isHokim = false,
    this.gender = '',
    this.birthDate,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'].toString(),
        phone: json['phone'] ?? '',
        name: json['name'] ?? '',
        avatar: json['avatar'],
        role: json['role'] ?? 'user',
        rating: (json['rating'] is num)
            ? (json['rating'] as num).toDouble()
            : double.tryParse('${json['rating']}') ?? 5.0,
        isHokim: json['is_hokim'] == true || json['is_staff'] == true,
        gender: json['gender'] ?? '',
        birthDate: json['birth_date'],
      );

  String get displayName => name.isNotEmpty ? name : phone;
}
