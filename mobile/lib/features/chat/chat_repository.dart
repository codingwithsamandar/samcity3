import '../../core/api_client.dart';
import 'chat_models.dart';

class ChatRepository {
  ChatRepository(this._api);
  final ApiClient _api;

  Future<List<ChatRoom>> rooms() async {
    final res = await _api.dio.get('/chat/rooms/');
    final results = (res.data['results'] as List?) ?? (res.data as List?) ?? [];
    return results.map((e) => ChatRoom.fromJson(e)).toList();
  }

  Future<ChatHistory> messages(String roomId, {int limit = 50, int offset = 0}) async {
    final res = await _api.dio.get('/chat/rooms/$roomId/messages/',
        queryParameters: {'limit': limit, 'offset': offset});
    return ChatHistory.fromJson(res.data);
  }

  Future<ChatMessage> send(String roomId, String text, {String? replyTo}) async {
    final res = await _api.dio.post('/chat/rooms/$roomId/messages/', data: {
      'text': text,
      if (replyTo != null) 'reply_to': replyTo,
    });
    return ChatMessage.fromJson(res.data);
  }
}
