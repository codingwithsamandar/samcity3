// Taksi haydovchi (taksist) paneli — mobil modellar.
import 'taxi_models.dart' show TaxiRoute;

class TaxistProfile {
  final String id;
  final String fullName;
  final String phone;
  final String carModel;
  final String region;
  final int tripsCount;
  final bool isOnline;
  final bool isActive;
  final double avgRating;
  final int reviewCount;

  TaxistProfile({
    required this.id,
    required this.fullName,
    required this.phone,
    this.carModel = '',
    this.region = '',
    this.tripsCount = 0,
    this.isOnline = false,
    this.isActive = true,
    this.avgRating = 0,
    this.reviewCount = 0,
  });

  factory TaxistProfile.fromJson(Map<String, dynamic> j) => TaxistProfile(
        id: j['id'].toString(),
        fullName: j['full_name'] ?? '',
        phone: j['phone'] ?? '',
        carModel: j['car_model'] ?? '',
        region: j['region'] ?? '',
        tripsCount: j['trips_count'] ?? 0,
        isOnline: j['is_online'] ?? false,
        isActive: j['is_active'] ?? true,
        avgRating: (j['avg_rating'] is num) ? (j['avg_rating'] as num).toDouble() : 0,
        reviewCount: j['review_count'] ?? 0,
      );
}

/// Haydovchi ko'radigan sayohat — yo'lovchi ma'lumoti bilan.
class DriverTrip {
  final String id;
  final String pointA;
  final String pointB;
  final bool isDelivery;
  final int price;
  final String status;
  final String statusDisplay;
  final String paymentStatus;
  final String passengerName;
  final String passengerPhone;
  final DateTime? createdAt;

  DriverTrip({
    required this.id,
    required this.pointA,
    required this.pointB,
    required this.isDelivery,
    required this.price,
    required this.status,
    required this.statusDisplay,
    required this.paymentStatus,
    this.passengerName = '',
    this.passengerPhone = '',
    this.createdAt,
  });

  factory DriverTrip.fromJson(Map<String, dynamic> j) => DriverTrip(
        id: j['id'].toString(),
        pointA: j['point_a'] ?? '',
        pointB: j['point_b'] ?? '',
        isDelivery: j['is_delivery'] ?? false,
        price: j['price'] ?? 0,
        status: j['status'] ?? '',
        statusDisplay: j['status_display'] ?? '',
        paymentStatus: j['payment_status'] ?? 'unpaid',
        passengerName: j['passenger_name'] ?? '',
        passengerPhone: j['passenger_phone'] ?? '',
        createdAt: DateTime.tryParse(j['created_at'] ?? ''),
      );
}

class TaxistStats {
  final int tripsCount;
  final int routesCount;
  final int activeCount;
  final int completedCount;
  final int earningsTotal;

  TaxistStats({
    this.tripsCount = 0,
    this.routesCount = 0,
    this.activeCount = 0,
    this.completedCount = 0,
    this.earningsTotal = 0,
  });

  factory TaxistStats.fromJson(Map<String, dynamic> j) => TaxistStats(
        tripsCount: j['trips_count'] ?? 0,
        routesCount: j['routes_count'] ?? 0,
        activeCount: j['active_count'] ?? 0,
        completedCount: j['completed_count'] ?? 0,
        earningsTotal: j['earnings_total'] ?? 0,
      );
}

/// Haydovchi paneli javobi. `registered=false` bo'lsa profil hali yo'q.
class TaxistPanel {
  final bool registered;
  final TaxistProfile? profile;
  final List<TaxiRoute> routes;
  final List<DriverTrip> active;
  final List<DriverTrip> history;
  final TaxistStats stats;

  TaxistPanel({
    required this.registered,
    this.profile,
    this.routes = const [],
    this.active = const [],
    this.history = const [],
    TaxistStats? stats,
  }) : stats = stats ?? TaxistStats();

  factory TaxistPanel.fromJson(Map<String, dynamic> j) {
    if (j['registered'] != true) {
      return TaxistPanel(registered: false);
    }
    List<DriverTrip> trips(String key) =>
        ((j[key] as List?) ?? []).map((e) => DriverTrip.fromJson(e)).toList();
    return TaxistPanel(
      registered: true,
      profile: j['taxist'] != null ? TaxistProfile.fromJson(j['taxist']) : null,
      routes: ((j['routes'] as List?) ?? [])
          .map((e) => TaxiRoute.fromJson(e))
          .toList(),
      active: trips('active'),
      history: trips('history'),
      stats: TaxistStats.fromJson((j['stats'] as Map<String, dynamic>?) ?? {}),
    );
  }
}
