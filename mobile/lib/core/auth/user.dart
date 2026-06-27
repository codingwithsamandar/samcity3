/// Foydalanuvchi modeli (API /auth/me/ va login javobidan).
class AppUser {
  final String id;
  final String phone;
  final String name;
  final String? avatar;
  final String role;
  final double rating;

  AppUser({
    required this.id,
    required this.phone,
    required this.name,
    this.avatar,
    required this.role,
    required this.rating,
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
      );

  String get displayName => name.isNotEmpty ? name : phone;
}
