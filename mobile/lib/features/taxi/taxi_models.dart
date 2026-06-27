import '../delivery/delivery_models.dart' show money;

class Taxist {
  final String id;
  final String fullName;
  final String phone;
  final String carModel;
  final String? photo;
  final String region;
  final int tripsCount;
  final bool isOnline;
  final double avgRating;
  final int reviewCount;
  final int? minPrice;

  Taxist({
    required this.id,
    required this.fullName,
    required this.phone,
    required this.carModel,
    this.photo,
    required this.region,
    required this.tripsCount,
    required this.isOnline,
    required this.avgRating,
    required this.reviewCount,
    this.minPrice,
  });

  factory Taxist.fromJson(Map<String, dynamic> j) => Taxist(
        id: j['id'].toString(),
        fullName: j['full_name'] ?? '',
        phone: j['phone'] ?? '',
        carModel: j['car_model'] ?? '',
        photo: j['photo'],
        region: j['region'] ?? '',
        tripsCount: j['trips_count'] ?? 0,
        isOnline: j['is_online'] ?? false,
        avgRating: (j['avg_rating'] is num) ? (j['avg_rating'] as num).toDouble() : 0,
        reviewCount: j['review_count'] ?? 0,
        minPrice: j['min_price'],
      );

  String get minPriceLabel =>
      minPrice == null ? '—' : "${money(minPrice!)} so'm dan";
}

class TaxiRoute {
  final String id;
  final String pointA;
  final String pointB;
  final int passengerPrice;
  final int? deliveryPrice;
  final String note;

  TaxiRoute({
    required this.id,
    required this.pointA,
    required this.pointB,
    required this.passengerPrice,
    this.deliveryPrice,
    required this.note,
  });

  factory TaxiRoute.fromJson(Map<String, dynamic> j) => TaxiRoute(
        id: j['id'].toString(),
        pointA: j['point_a'] ?? '',
        pointB: j['point_b'] ?? '',
        passengerPrice: j['passenger_price'] ?? 0,
        deliveryPrice: j['delivery_price'],
        note: j['note'] ?? '',
      );
}

class TaxistDetail {
  final Taxist taxist;
  final List<TaxiRoute> routes;
  final String? carFullName;
  final String? carPlate;
  final int? carSeats;

  TaxistDetail({
    required this.taxist,
    required this.routes,
    this.carFullName,
    this.carPlate,
    this.carSeats,
  });

  factory TaxistDetail.fromJson(Map<String, dynamic> j) {
    final car = j['car'];
    return TaxistDetail(
      taxist: Taxist.fromJson(j),
      routes: ((j['routes'] as List?) ?? [])
          .map((e) => TaxiRoute.fromJson(e))
          .toList(),
      carFullName: car?['full_name'],
      carPlate: car?['plate_number'],
      carSeats: car?['seats'],
    );
  }
}

class Trip {
  final String id;
  final String pointA;
  final String pointB;
  final bool isDelivery;
  final int price;
  final String status;
  final String statusDisplay;
  final String paymentStatus;
  final String taxistName;
  final String? taxistPhone;
  final DateTime? createdAt;

  Trip({
    required this.id,
    required this.pointA,
    required this.pointB,
    required this.isDelivery,
    required this.price,
    required this.status,
    required this.statusDisplay,
    required this.paymentStatus,
    required this.taxistName,
    this.taxistPhone,
    this.createdAt,
  });

  factory Trip.fromJson(Map<String, dynamic> j) => Trip(
        id: j['id'].toString(),
        pointA: j['point_a'] ?? '',
        pointB: j['point_b'] ?? '',
        isDelivery: j['is_delivery'] ?? false,
        price: j['price'] ?? 0,
        status: j['status'] ?? '',
        statusDisplay: j['status_display'] ?? '',
        paymentStatus: j['payment_status'] ?? 'unpaid',
        taxistName: j['taxist']?['full_name'] ?? '',
        taxistPhone: j['taxist']?['phone'],
        createdAt: DateTime.tryParse(j['created_at'] ?? ''),
      );

  String get priceLabel => "${money(price)} so'm";
}

class TaxiService {
  final String id;
  final String name;
  final String shortNumber;
  final String phone;
  final String? logo;
  final int basePrice;
  final int pricePerKm;
  final String workingHours;
  final double avgRating;

  TaxiService({
    required this.id,
    required this.name,
    required this.shortNumber,
    required this.phone,
    this.logo,
    required this.basePrice,
    required this.pricePerKm,
    required this.workingHours,
    required this.avgRating,
  });

  factory TaxiService.fromJson(Map<String, dynamic> j) => TaxiService(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        shortNumber: j['short_number'] ?? '',
        phone: j['phone'] ?? '',
        logo: j['logo'],
        basePrice: j['base_price'] ?? 0,
        pricePerKm: j['price_per_km'] ?? 0,
        workingHours: j['working_hours'] ?? '',
        avgRating: (j['avg_rating'] is num) ? (j['avg_rating'] as num).toDouble() : 0,
      );
}
