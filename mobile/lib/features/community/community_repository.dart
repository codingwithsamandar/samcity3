import '../../core/api_client.dart';
import 'community_models.dart';

class CommunityRepository {
  CommunityRepository(this._api);
  final ApiClient _api;

  Future<List<Poll>> polls() async {
    final res = await _api.dio.get('/community/polls/');
    return ((res.data['results'] as List?) ?? [])
        .map((e) => Poll.fromJson(e)).toList();
  }

  Future<Poll> vote(String pollId, List<int> optionIds) async {
    final res = await _api.dio.post('/community/polls/$pollId/vote/',
        data: {'options': optionIds});
    return Poll.fromJson(res.data);
  }

  Future<(List<HelpCategory>, List<HelpRequest>)> help({String? category}) async {
    final res = await _api.dio.get('/community/help/', queryParameters: {
      if (category != null && category.isNotEmpty) 'category': category,
    });
    final cats = ((res.data['categories'] as List?) ?? [])
        .map((e) => HelpCategory.fromJson(e)).toList();
    final items = ((res.data['results'] as List?) ?? [])
        .map((e) => HelpRequest.fromJson(e)).toList();
    return (cats, items);
  }

  Future<HelpRequest> createHelp({
    required String title,
    required String description,
    String kind = 'request',
    String category = 'general',
    String location = '',
    String phone = '',
    bool isUrgent = false,
  }) async {
    final res = await _api.dio.post('/community/help/', data: {
      'title': title, 'description': description, 'kind': kind,
      'category': category, 'location': location, 'phone': phone,
      'is_urgent': isUrgent,
    });
    return HelpRequest.fromJson(res.data);
  }
}
