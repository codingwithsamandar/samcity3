import '../../core/api_client.dart';
import '../community/community_models.dart';
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

  /// Mahalla do'koni ochish uchun ariza (admin tasdiqlaguncha 'pending').
  Future<void> createStoreRequest(String neighborhoodId,
      {required String name, String description = '', String address = '', String phone = ''}) async {
    await _api.dio.post('/stores/request/', data: {
      'neighborhood': neighborhoodId,
      'name': name,
      'description': description,
      'address': address,
      'phone': phone,
    });
  }

  // ── So'rovnomalar (mahallaga cheklangan) ──
  Future<(bool, List<Poll>)> polls(String neighborhoodId) async {
    final res = await _api.dio.get('/community/polls/',
        queryParameters: {'neighborhood': neighborhoodId});
    final isAdmin = res.data['is_admin'] == true;
    final items = ((res.data['results'] as List?) ?? [])
        .map((e) => Poll.fromJson(e)).toList();
    return (isAdmin, items);
  }

  Future<Poll> votePoll(String pollId, List<int> optionIds) async {
    final res = await _api.dio.post('/community/polls/$pollId/vote/',
        data: {'options': optionIds});
    return Poll.fromJson(res.data);
  }

  /// Admin yangi so'rovnoma ochadi (variantlar bo'sh bo'lsa "Ha/Yo'q").
  Future<Poll> createPoll(String neighborhoodId,
      {required String question, String description = '', List<String> options = const []}) async {
    final res = await _api.dio.post('/community/polls/', data: {
      'neighborhood': neighborhoodId,
      'question': question,
      'description': description,
      'options': options,
    });
    return Poll.fromJson(res.data);
  }

  Future<List<PollComment>> pollComments(String pollId, {String? text}) async {
    final res = text == null
        ? await _api.dio.get('/community/polls/$pollId/comments/')
        : await _api.dio.post('/community/polls/$pollId/comments/', data: {'text': text});
    return ((res.data['results'] as List?) ?? [])
        .map((e) => PollComment.fromJson(e)).toList();
  }

  // ── Valentyorlik / yordam (mahallaga cheklangan) ──
  Future<List<HelpRequest>> help(String neighborhoodId) async {
    final res = await _api.dio.get('/community/help/',
        queryParameters: {'neighborhood': neighborhoodId});
    return ((res.data['results'] as List?) ?? [])
        .map((e) => HelpRequest.fromJson(e)).toList();
  }

  Future<void> createHelp(String neighborhoodId,
      {required String title, required String description,
      String kind = 'offer', String category = 'volunteer',
      String location = '', String phone = ''}) async {
    await _api.dio.post('/community/help/', data: {
      'neighborhood': neighborhoodId,
      'title': title, 'description': description, 'kind': kind,
      'category': category, 'location': location, 'phone': phone,
    });
  }
}
