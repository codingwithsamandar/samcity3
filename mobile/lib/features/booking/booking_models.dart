import '../delivery/delivery_models.dart' show money;

class Venue {
  final String id;
  final String name;
  final String venueType;
  final String venueTypeDisplay;
  final String address;
  final String phone;
  final String? image;
  final int? capacity;
  final int? pricePerDay;
  final int? pricePerHour;

  Venue({
    required this.id,
    required this.name,
    required this.venueType,
    required this.venueTypeDisplay,
    required this.address,
    required this.phone,
    this.image,
    this.capacity,
    this.pricePerDay,
    this.pricePerHour,
  });

  factory Venue.fromJson(Map<String, dynamic> j) => Venue(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        venueType: j['venue_type'] ?? 'other',
        venueTypeDisplay: j['venue_type_display'] ?? '',
        address: j['address'] ?? '',
        phone: j['phone'] ?? '',
        image: j['image'],
        capacity: j['capacity'],
        pricePerDay: j['price_per_day'],
        pricePerHour: j['price_per_hour'],
      );

  String get priceLabel {
    if (pricePerDay != null) return "${money(pricePerDay!)} so'm / kun";
    if (pricePerHour != null) return "${money(pricePerHour!)} so'm / soat";
    return 'Narx kelishiladi';
  }
}

class VenueService {
  final String id;
  final String name;
  final int price;
  final int durationMinutes;

  VenueService({required this.id, required this.name, required this.price,
    required this.durationMinutes});

  factory VenueService.fromJson(Map<String, dynamic> j) => VenueService(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        price: (j['price'] is num) ? (j['price'] as num).toInt() : 0,
        durationMinutes: j['duration_minutes'] ?? 30,
      );

  String get priceLabel => "${money(price)} so'm";
}

class VenueStaff {
  final String id;
  final String name;
  final String specialty;
  final String? photo;
  final String bio;
  final double rating;
  final int reviewsCount;
  final int completedCount;
  final int experienceYears;
  final bool available; // staff-at javobida — shu vaqtда bo'shmi

  VenueStaff({
    required this.id,
    required this.name,
    required this.specialty,
    this.photo,
    this.bio = '',
    this.rating = 0,
    this.reviewsCount = 0,
    this.completedCount = 0,
    this.experienceYears = 0,
    this.available = true,
  });

  factory VenueStaff.fromJson(Map<String, dynamic> j) => VenueStaff(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        specialty: j['specialty'] ?? '',
        photo: j['photo'],
        bio: j['bio'] ?? '',
        rating: (j['rating'] is num) ? (j['rating'] as num).toDouble() : 0,
        reviewsCount: j['reviews_count'] ?? 0,
        completedCount: j['completed_count'] ?? 0,
        experienceYears: j['experience_years'] ?? 0,
        available: j['available'] ?? true,
      );
}

class VenueDetail {
  final Venue venue;
  final String description;
  final List<String> bookedDates;
  final List<VenueService> services;
  final List<VenueStaff> staff;
  final bool usesSlots;
  final bool prepayRequired;
  final int penaltyPercent;
  final double? latitude;
  final double? longitude;
  /// Xodim uchun joyga mos so'z: klinikada «Shifokor», aks holda «Usta».
  final String staffLabel;
  /// Bron oynasi — serverdan keladi (tur bo'yicha turlicha). Taqvim shu
  /// chegaradan narisiga ruxsat bermasin, aks holda server rad etadi.
  final int maxAheadDays;
  final DateTime? bookFrom;
  final DateTime? bookUntil;

  VenueDetail({
    required this.venue,
    required this.description,
    required this.bookedDates,
    this.services = const [],
    this.staff = const [],
    this.usesSlots = false,
    this.prepayRequired = true,
    this.penaltyPercent = 0,
    this.latitude,
    this.longitude,
    this.staffLabel = 'Usta',
    this.maxAheadDays = 7,
    this.bookFrom,
    this.bookUntil,
  });

  factory VenueDetail.fromJson(Map<String, dynamic> j) => VenueDetail(
        venue: Venue.fromJson(j),
        description: j['description'] ?? '',
        bookedDates: ((j['booked_dates'] as List?) ?? [])
            .map((e) => e.toString())
            .toList(),
        services: ((j['services'] as List?) ?? [])
            .map((e) => VenueService.fromJson(e))
            .toList(),
        staff: ((j['staff'] as List?) ?? [])
            .map((e) => VenueStaff.fromJson(e))
            .toList(),
        usesSlots: j['uses_slots'] ?? false,
        prepayRequired: j['prepay_required'] ?? true,
        penaltyPercent: j['penalty_percent'] ?? 0,
        latitude: (j['latitude'] is num) ? (j['latitude'] as num).toDouble() : null,
        longitude: (j['longitude'] is num) ? (j['longitude'] as num).toDouble() : null,
        staffLabel: j['staff_label'] ?? 'Usta',
        maxAheadDays: j['max_ahead_days'] ?? 7,
        bookFrom: DateTime.tryParse(j['book_from']?.toString() ?? ''),
        bookUntil: DateTime.tryParse(j['book_until']?.toString() ?? ''),
      );
}

/// Egasi paneli uchun to'liq joy — tahrir formasi va xizmat/usta boshqaruvi.
class OwnerVenue {
  final String id;
  final String name;
  final String venueType;
  final String venueTypeDisplay;
  final String description;
  final String address;
  final String phone;
  final String? image;
  final int? capacity;
  final int? pricePerDay;
  final int? pricePerHour;
  final String? workingHoursStart; // "HH:MM:SS"
  final String? workingHoursEnd;
  final double? latitude;
  final double? longitude;
  final bool prepayRequired;
  final int cancelPenaltyPercent;
  final int graceMinutes;
  final bool isActive;
  final bool usesSlots;
  /// Xodim uchun joyga mos so'z: klinikada «Shifokor», aks holda «Usta».
  final String staffLabel;
  final List<VenueService> services;
  final List<VenueStaff> staff;

  OwnerVenue({
    required this.id,
    required this.name,
    required this.venueType,
    this.venueTypeDisplay = '',
    this.description = '',
    this.address = '',
    this.phone = '',
    this.image,
    this.capacity,
    this.pricePerDay,
    this.pricePerHour,
    this.workingHoursStart,
    this.workingHoursEnd,
    this.latitude,
    this.longitude,
    this.prepayRequired = true,
    this.cancelPenaltyPercent = 10,
    this.graceMinutes = 15,
    this.isActive = true,
    this.usesSlots = false,
    this.staffLabel = 'Usta',
    this.services = const [],
    this.staff = const [],
  });

  factory OwnerVenue.fromJson(Map<String, dynamic> j) => OwnerVenue(
        id: j['id'].toString(),
        name: j['name'] ?? '',
        venueType: j['venue_type'] ?? 'other',
        venueTypeDisplay: j['venue_type_display'] ?? '',
        description: j['description'] ?? '',
        address: j['address'] ?? '',
        phone: j['phone'] ?? '',
        image: j['image'],
        capacity: j['capacity'],
        pricePerDay: j['price_per_day'],
        pricePerHour: j['price_per_hour'],
        workingHoursStart: j['working_hours_start'],
        workingHoursEnd: j['working_hours_end'],
        latitude: (j['latitude'] is num) ? (j['latitude'] as num).toDouble() : null,
        longitude: (j['longitude'] is num) ? (j['longitude'] as num).toDouble() : null,
        prepayRequired: j['prepay_required'] ?? true,
        cancelPenaltyPercent: j['cancel_penalty_percent'] ?? 10,
        graceMinutes: j['grace_minutes'] ?? 15,
        isActive: j['is_active'] ?? true,
        usesSlots: j['uses_slots'] ?? false,
        staffLabel: j['staff_label'] ?? 'Usta',
        services: ((j['services'] as List?) ?? [])
            .map((e) => VenueService.fromJson(e))
            .toList(),
        staff: ((j['staff'] as List?) ?? [])
            .map((e) => VenueStaff.fromJson(e))
            .toList(),
      );
}

class VenueBooking {
  final String id;
  final String venueName;
  final String venueType;
  final String status;
  final String statusDisplay;
  final String bookingDate;
  final int guests;
  final int? totalAmount;
  final DateTime? createdAt;
  // Egasi paneli uchun: bron qilgan mijoz + qo'shimcha ma'lumot.
  final String customerName;
  final String customerPhone;
  final String message;
  final String? startTime;

  VenueBooking({
    required this.id,
    required this.venueName,
    required this.venueType,
    required this.status,
    required this.statusDisplay,
    required this.bookingDate,
    required this.guests,
    this.totalAmount,
    this.createdAt,
    this.customerName = '',
    this.customerPhone = '',
    this.message = '',
    this.startTime,
  });

  factory VenueBooking.fromJson(Map<String, dynamic> j) => VenueBooking(
        id: j['id'].toString(),
        venueName: j['venue_name'] ?? '',
        venueType: j['venue_type'] ?? '',
        status: j['status'] ?? 'pending',
        statusDisplay: j['status_display'] ?? '',
        bookingDate: j['booking_date'] ?? '',
        guests: j['guests'] ?? 1,
        totalAmount: j['total_amount'],
        createdAt: DateTime.tryParse(j['created_at'] ?? ''),
        customerName: j['customer_name'] ?? '',
        customerPhone: j['customer_phone'] ?? '',
        message: j['message'] ?? '',
        startTime: j['start_time'],
      );

  String get amountLabel =>
      totalAmount == null ? '—' : "${money(totalAmount!)} so'm";
}
