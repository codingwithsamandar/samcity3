import '../../core/api_client.dart';
import 'place_model.dart';

class PlacesRepository {
  PlacesRepository(this._api);
  final ApiClient _api;

  Future<PlacesData> places({String? category}) async {
    final res = await _api.dio.get('/places/', queryParameters: {
      if (category != null && category.isNotEmpty) 'category': category,
    });
    final cats = ((res.data['categories'] as List?) ?? [])
        .map((e) => PlaceCategory.fromJson(e))
        .toList();
    final places = ((res.data['results'] as List?) ?? [])
        .map((e) => Place.fromJson(e))
        .toList();
    return PlacesData(categories: cats, places: places);
  }
}
