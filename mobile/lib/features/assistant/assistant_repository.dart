import '../../core/api_client.dart';
import 'assistant_models.dart';

/// AI yordamchi — mobil REST API klienti.
/// `POST /api/assistant/chat/` (ochiq, autentifikatsiyasiz).
class AssistantRepository {
  AssistantRepository(this._api);
  final ApiClient _api;

  Future<AiResponse> chat(
    String message, {
    double? lat,
    double? lng,
    List<Map<String, String>>? history,
    Map<String, dynamic>? context,
  }) async {
    final res = await _api.dio.post('/assistant/chat/', data: {
      'message': message,
      if (lat != null && lng != null) 'location': {'lat': lat, 'lng': lng},
      if (history != null && history.isNotEmpty) 'history': history,
      if (context != null && context.isNotEmpty) 'context': context,
    });
    final data = res.data is Map ? (res.data as Map).cast<String, dynamic>() : <String, dynamic>{};
    return AiResponse.fromJson(data);
  }
}
