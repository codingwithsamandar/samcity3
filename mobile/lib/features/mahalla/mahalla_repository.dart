import '../../core/api_client.dart';
import 'mahalla_models.dart';

class MahallaRepository {
  MahallaRepository(this._api);
  final ApiClient _api;

  /// Mahallalar ro'yxati (+ foydalanuvchi mahallasi id).
  Future<(String?, List<Neighborhood>)> list() async {
    final res = await _api.dio.get('/mahalla/');
    final my = res.data['my_neighborhood']?.toString();
    final items = ((res.data['results'] as List?) ?? [])
        .map((e) => Neighborhood.fromJson(e)).toList();
    return (my, items);
  }

  Future<MahallaDetail> detail(String id) async {
    final res = await _api.dio.get('/mahalla/$id/');
    return MahallaDetail.fromJson(res.data);
  }

  /// Murojaatlar (admin barchasini, oddiy foydalanuvchi o'zinikini).
  Future<(bool, List<Complaint>)> complaints(String id) async {
    final res = await _api.dio.get('/mahalla/$id/complaints/');
    final bool isAdmin = res.data['is_admin'] == true;
    final items = ((res.data['results'] as List?) ?? [])
        .map((e) => Complaint.fromJson(e)).toList();
    return (isAdmin, items);
  }

  Future<Complaint> createComplaint(String id,
      {required String category, required String title, required String text}) async {
    final res = await _api.dio.post('/mahalla/$id/complaints/',
        data: {'category': category, 'title': title, 'text': text});
    return Complaint.fromJson(res.data);
  }

  Future<Complaint> updateComplaintStatus(String reqId,
      {String? status, String? response}) async {
    final res = await _api.dio.post('/mahalla/complaints/$reqId/status/', data: {
      if (status != null) 'status': status,
      if (response != null) 'response': response,
    });
    return Complaint.fromJson(res.data);
  }

  Future<Announcement> createAnnouncement(String id,
      {required String title, required String text}) async {
    final res = await _api.dio.post('/mahalla/$id/announce/',
        data: {'title': title, 'text': text});
    return Announcement.fromJson(res.data);
  }
}
