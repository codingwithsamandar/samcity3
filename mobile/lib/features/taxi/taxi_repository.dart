import '../../core/api_client.dart';
import 'taxi_models.dart';

class TaxiRepository {
  TaxiRepository(this._api);
  final ApiClient _api;

  Future<List<Taxist>> taxists({String? query}) async {
    final res = await _api.dio.get('/taxi/taxists/', queryParameters: {
      if (query != null && query.isNotEmpty) 'search': query,
    });
    final results = (res.data['results'] as List?) ?? [];
    return results.map((e) => Taxist.fromJson(e)).toList();
  }

  Future<TaxistDetail> taxistDetail(String id) async {
    final res = await _api.dio.get('/taxi/taxists/$id/');
    return TaxistDetail.fromJson(res.data);
  }

  Future<List<TaxiService>> services() async {
    final res = await _api.dio.get('/taxi/services/');
    final results = (res.data['results'] as List?) ?? [];
    return results.map((e) => TaxiService.fromJson(e)).toList();
  }

  Future<List<Trip>> myTrips() async {
    final res = await _api.dio.get('/taxi/trips/');
    final results = (res.data['results'] as List?) ?? [];
    return results.map((e) => Trip.fromJson(e)).toList();
  }

  Future<Trip> book({required String routeId, bool isDelivery = false}) async {
    final res = await _api.dio.post('/taxi/trips/',
        data: {'route_id': routeId, 'is_delivery': isDelivery});
    return Trip.fromJson(res.data);
  }
}
