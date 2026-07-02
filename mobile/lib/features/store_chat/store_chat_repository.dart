import '../../core/api_client.dart';
import 'store_chat_models.dart';

class StoreChatRepository {
  StoreChatRepository(this._api);
  final ApiClient _api;

  /// Mijoz do'kon bilan suhbatni ochadi (yoki mavjudini qaytaradi).
  Future<StoreChatThread> start(String storeId) async {
    final res = await _api.dio.post('/stores/$storeId/chat/');
    return StoreChatThread.fromJson(res.data);
  }

  /// Foydalanuvchining barcha suhbatlari (mijoz + do'kon egasi sifatida).
  Future<List<StoreChatThread>> threads() async {
    final res = await _api.dio.get('/delivery/chat/threads/');
    final results = (res.data['results'] as List?) ?? [];
    return results.map((e) => StoreChatThread.fromJson(e)).toList();
  }

  /// Bitta suhbat: xabarlar tarixi.
  Future<List<StoreChatMessage>> messages(String threadId) async {
    final res = await _api.dio.get('/delivery/chat/threads/$threadId/');
    final results = (res.data['messages'] as List?) ?? [];
    return results.map((e) => StoreChatMessage.fromJson(e)).toList();
  }

  /// Xabar yuborish (REST fallback — WebSocket ishlamasa).
  Future<StoreChatMessage> send(String threadId, String text) async {
    final res = await _api.dio.post('/delivery/chat/threads/$threadId/',
        data: {'text': text});
    return StoreChatMessage.fromJson(res.data);
  }
}
