import 'package:dio/dio.dart';

import '../../core/api_client.dart';
import 'hokim_models.dart';

class HokimRepository {
  HokimRepository(this._api);
  final ApiClient _api;

  /// Foydalanuvchi hokim bo'lgan tuman(lar) + e'lonlar.
  Future<List<HokimDistrict>> panel() async {
    final res = await _api.dio.get('/hokim/');
    return ((res.data['results'] as List?) ?? [])
        .map((e) => HokimDistrict.fromJson(e))
        .toList();
  }

  /// Tuman hokimi rasmiy e'lon joylaydi (→ butun tuman aholisiga push).
  /// [image] ixtiyoriy — biriktirilsa multipart bo'lib yuboriladi.
  Future<DistrictAnnouncement> announce(String districtId,
      {required String title, required String text, MultipartFile? image}) async {
    final dynamic data = image == null
        ? {'title': title, 'text': text}
        : FormData.fromMap({'title': title, 'text': text, 'image': image});
    final res = await _api.dio.post('/hokim/$districtId/announce/', data: data);
    return DistrictAnnouncement.fromJson(res.data);
  }
}
