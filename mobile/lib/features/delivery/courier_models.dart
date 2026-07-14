// Kuryer (yetkazib beruvchi) — mobil modellar.
import 'delivery_models.dart';

class CourierProfile {
  final String id;
  final String fullName;
  final String phone;
  final String vehicleType;
  final String vehicleDisplay;
  final String vehicleNumber;
  final bool isAvailable;
  final double avgRating;
  final int reviewCount;

  CourierProfile({
    required this.id,
    required this.fullName,
    required this.phone,
    required this.vehicleType,
    this.vehicleDisplay = '',
    this.vehicleNumber = '',
    this.isAvailable = true,
    this.avgRating = 0,
    this.reviewCount = 0,
  });

  factory CourierProfile.fromJson(Map<String, dynamic> j) => CourierProfile(
        id: j['id'].toString(),
        fullName: j['full_name'] ?? '',
        phone: j['phone'] ?? '',
        vehicleType: j['vehicle_type'] ?? 'moto',
        vehicleDisplay: j['vehicle_display'] ?? '',
        vehicleNumber: j['vehicle_number'] ?? '',
        isAvailable: j['is_available'] ?? true,
        avgRating: (j['avg_rating'] is num) ? (j['avg_rating'] as num).toDouble() : 0,
        reviewCount: j['review_count'] ?? 0,
      );
}

class CourierStats {
  final int deliveredCount;
  final int activeCount;
  final int earningsTotal;
  final int earningsToday;
  final int earningsWeek;
  final int earningsMonth;

  CourierStats({
    this.deliveredCount = 0,
    this.activeCount = 0,
    this.earningsTotal = 0,
    this.earningsToday = 0,
    this.earningsWeek = 0,
    this.earningsMonth = 0,
  });

  factory CourierStats.fromJson(Map<String, dynamic> j) => CourierStats(
        deliveredCount: j['delivered_count'] ?? 0,
        activeCount: j['active_count'] ?? 0,
        earningsTotal: j['earnings_total'] ?? 0,
        earningsToday: j['earnings_today'] ?? 0,
        earningsWeek: j['earnings_week'] ?? 0,
        earningsMonth: j['earnings_month'] ?? 0,
      );
}

/// Kuryer dashboard javobi. `registered=false` bo'lsa profil hali yo'q.
class CourierDashboard {
  final bool registered;
  final CourierProfile? profile;
  final List<DeliveryOrder> available;
  final List<DeliveryOrder> active;
  final List<DeliveryOrder> history;
  final CourierStats stats;

  CourierDashboard({
    required this.registered,
    this.profile,
    this.available = const [],
    this.active = const [],
    this.history = const [],
    CourierStats? stats,
  }) : stats = stats ?? CourierStats();

  factory CourierDashboard.fromJson(Map<String, dynamic> j) {
    if (j['registered'] != true) {
      return CourierDashboard(registered: false);
    }
    List<DeliveryOrder> parse(String key) =>
        ((j[key] as List?) ?? []).map((e) => DeliveryOrder.fromJson(e)).toList();
    return CourierDashboard(
      registered: true,
      profile: j['driver'] != null ? CourierProfile.fromJson(j['driver']) : null,
      available: parse('available'),
      active: parse('active'),
      history: parse('history'),
      stats: CourierStats.fromJson((j['stats'] as Map<String, dynamic>?) ?? {}),
    );
  }
}
