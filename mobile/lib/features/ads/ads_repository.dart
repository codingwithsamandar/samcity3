import 'package:dio/dio.dart';

import '../../core/api_client.dart';
import 'ad_model.dart';

/// Sahifalangan e'lonlar natijasi.
class AdsPage {
  const AdsPage({required this.items, required this.hasNext, required this.page});
  final List<AdListItem> items;
  final bool hasNext;
  final int page;
}

/// E'lonlar API'si bilan ishlash.
class AdsRepository {
  AdsRepository(this._api);
  final ApiClient _api;

  Future<AdsPage> list({
    String? query,
    String? category,
    String? ordering,
    int page = 1,
  }) async {
    final res = await _api.dio.get('/ads/', queryParameters: {
      if (query != null && query.isNotEmpty) 'search': query,
      if (category != null && category.isNotEmpty) 'category': category,
      if (ordering != null && ordering.isNotEmpty) 'ordering': ordering,
      'page': page,
    });
    final results = (res.data['results'] as List?) ?? [];
    final next = res.data['next'];
    return AdsPage(
      items: results.map((e) => AdListItem.fromJson(e)).toList(),
      hasNext: next != null && next.toString().isNotEmpty,
      page: page,
    );
  }

  Future<AdDetail> detail(String id) async {
    final res = await _api.dio.get('/ads/$id/');
    return AdDetail.fromJson(res.data);
  }

  Future<void> create({
    required String title,
    required String category,
    String description = '',
    int? price,
    required String priceType,
    String location = '',
    String contactPhone = '',
    List<MultipartFile> images = const [],
  }) async {
    final form = FormData.fromMap({
      'title': title,
      'category': category,
      'description': description,
      if (price != null) 'price': price,
      'price_type': priceType,
      'location': location,
      'contact_phone': contactPhone,
      if (images.isNotEmpty) 'uploaded_images': images,
    });
    await _api.dio.post('/ads/', data: form);
  }

  Future<bool> toggleFavorite(String id, {required bool add}) async {
    final res = await _api.dio.request(
      '/ads/$id/favorite/',
      options: Options(method: add ? 'POST' : 'DELETE'),
    );
    return res.data['favorited'] ?? add;
  }
}
