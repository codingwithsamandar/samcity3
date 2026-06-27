import '../../core/api_client.dart';
import 'booking_models.dart';

class BookingRepository {
  BookingRepository(this._api);
  final ApiClient _api;

  Future<List<Venue>> venues({String? type, String? query}) async {
    final res = await _api.dio.get('/booking/venues/', queryParameters: {
      if (type != null && type.isNotEmpty) 'venue_type': type,
      if (query != null && query.isNotEmpty) 'search': query,
    });
    final results = (res.data['results'] as List?) ?? [];
    return results.map((e) => Venue.fromJson(e)).toList();
  }

  Future<VenueDetail> detail(String id) async {
    final res = await _api.dio.get('/booking/venues/$id/');
    return VenueDetail.fromJson(res.data);
  }

  /// Berilgan sana uchun bo'sh vaqt-slotlar.
  Future<List<String>> slots(String venueId,
      {required String date, String? staff, String? service}) async {
    final res = await _api.dio.get('/booking/venues/$venueId/slots/',
        queryParameters: {
          'date': date,
          if (staff != null) 'staff': staff,
          if (service != null) 'service': service,
        });
    return ((res.data['slots'] as List?) ?? []).map((e) => e.toString()).toList();
  }

  /// Berilgan vaqtда bo'sh/band ustalar (rasm, baho, statistika bilan).
  Future<List<VenueStaff>> staffAt(String venueId,
      {required String date, required String time, String? service}) async {
    final res = await _api.dio.get('/booking/venues/$venueId/staff-at/',
        queryParameters: {
          'date': date,
          'time': time,
          if (service != null) 'service': service,
        });
    return ((res.data['staff'] as List?) ?? [])
        .map((e) => VenueStaff.fromJson(e))
        .toList();
  }

  Future<VenueBooking> book(
    String venueId, {
    required String date,
    String? startTime,
    String? endTime,
    String? service,
    String? staff,
    int guests = 1,
    String message = '',
  }) async {
    final res = await _api.dio.post('/booking/venues/$venueId/book/', data: {
      'booking_date': date,
      if (startTime != null) 'start_time': startTime,
      if (endTime != null) 'end_time': endTime,
      if (service != null) 'service': service,
      if (staff != null) 'staff': staff,
      'guests': guests,
      'message': message,
    });
    return VenueBooking.fromJson(res.data);
  }

  Future<List<VenueBooking>> myBookings() async {
    final res = await _api.dio.get('/booking/bookings/');
    final results = (res.data['results'] as List?) ?? [];
    return results.map((e) => VenueBooking.fromJson(e)).toList();
  }

  Future<void> cancel(String bookingId) async {
    await _api.dio.post('/booking/bookings/$bookingId/cancel/');
  }
}
