import '../../core/api_client.dart';
import 'jobs_models.dart';

class JobsRepository {
  JobsRepository(this._api);
  final ApiClient _api;

  Future<List<JobAd>> jobs({String? query}) async {
    final res = await _api.dio.get('/jobs/', queryParameters: {
      if (query != null && query.isNotEmpty) 'search': query,
    });
    return ((res.data['results'] as List?) ?? [])
        .map((e) => JobAd.fromJson(e)).toList();
  }

  Future<List<ResumeAd>> resumes({String? query}) async {
    final res = await _api.dio.get('/resumes/', queryParameters: {
      if (query != null && query.isNotEmpty) 'search': query,
    });
    return ((res.data['results'] as List?) ?? [])
        .map((e) => ResumeAd.fromJson(e)).toList();
  }

  Future<void> createJob(Map<String, dynamic> data) async {
    await _api.dio.post('/jobs/', data: data);
  }

  Future<void> createResume(Map<String, dynamic> data) async {
    await _api.dio.post('/resumes/', data: data);
  }
}
