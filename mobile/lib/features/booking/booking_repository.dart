import 'package:dio/dio.dart';

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

  // ── Egasi (to'yxona/joy) bron boshqaruvi ──
  /// Egaga tegishli joylardagi bronlar: (kutilayotgan, boshqalar).
  Future<(List<VenueBooking>, List<VenueBooking>)> ownerBookings() async {
    final res = await _api.dio.get('/booking/manage/');
    List<VenueBooking> parse(String key) =>
        ((res.data[key] as List?) ?? []).map((e) => VenueBooking.fromJson(e)).toList();
    return (parse('pending'), parse('others'));
  }

  /// action: confirm / cancel / complete
  Future<VenueBooking> ownerAction(String bookingId, String action) async {
    final res = await _api.dio.post('/booking/manage/$bookingId/$action/');
    return VenueBooking.fromJson(res.data);
  }

  Future<List<Venue>> myVenues() async {
    final res = await _api.dio.get('/booking/my-venues/');
    return ((res.data as List?) ?? []).map((e) => Venue.fromJson(e)).toList();
  }

  // ── Egasi joy setup (venue create/edit + xizmat/usta) ──
  /// Fayl bo'lsa multipart (barcha qiymatlar matnга aylantiriladi), aks holda JSON.
  Object _payload(Map<String, dynamic> data, {String? fileField, MultipartFile? file}) {
    if (file == null) return data;
    final m = <String, dynamic>{};
    data.forEach((k, v) {
      if (v != null) m[k] = (v is bool) ? (v ? 'true' : 'false') : '$v';
    });
    m[fileField!] = file;
    return FormData.fromMap(m);
  }

  Future<OwnerVenue> ownerVenueDetail(String id) async {
    final res = await _api.dio.get('/booking/my-venues/$id/');
    return OwnerVenue.fromJson(res.data as Map<String, dynamic>);
  }

  Future<OwnerVenue> createVenue(Map<String, dynamic> data, {MultipartFile? image}) async {
    final res = await _api.dio.post('/booking/my-venues/',
        data: _payload(data, fileField: 'image', file: image));
    return OwnerVenue.fromJson(res.data as Map<String, dynamic>);
  }

  Future<OwnerVenue> updateVenue(String id, Map<String, dynamic> data,
      {MultipartFile? image}) async {
    final res = await _api.dio.patch('/booking/my-venues/$id/',
        data: _payload(data, fileField: 'image', file: image));
    return OwnerVenue.fromJson(res.data as Map<String, dynamic>);
  }

  Future<void> deleteVenue(String id) async {
    await _api.dio.delete('/booking/my-venues/$id/');
  }

  Future<VenueService> addService(String venueId,
      {required String name, required int price, int durationMinutes = 30}) async {
    final res = await _api.dio.post('/booking/my-venues/$venueId/services/', data: {
      'name': name, 'price': price, 'duration_minutes': durationMinutes,
    });
    return VenueService.fromJson(res.data as Map<String, dynamic>);
  }

  Future<void> deleteService(String serviceId) async {
    await _api.dio.delete('/booking/my-venues/services/$serviceId/');
  }

  Future<VenueStaff> addStaff(String venueId,
      {required String name, String specialty = '', MultipartFile? photo}) async {
    final res = await _api.dio.post('/booking/my-venues/$venueId/staff/',
        data: _payload({
          'name': name,
          if (specialty.isNotEmpty) 'specialty': specialty,
        }, fileField: 'photo', file: photo));
    return VenueStaff.fromJson(res.data as Map<String, dynamic>);
  }

  Future<void> deleteStaff(String staffId) async {
    await _api.dio.delete('/booking/my-venues/staff/$staffId/');
  }
}
