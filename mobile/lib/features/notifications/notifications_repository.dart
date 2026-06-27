import '../../core/api_client.dart';
import 'notification_model.dart';

class NotificationsRepository {
  NotificationsRepository(this._api);
  final ApiClient _api;

  /// Bildirishnomalar ro'yxati. [unreadOnly] — faqat o'qilmaganlar.
  Future<NotificationPage> list({
    bool unreadOnly = false,
    int limit = 30,
    int offset = 0,
  }) async {
    final res = await _api.dio.get('/notifications/', queryParameters: {
      'limit': limit,
      'offset': offset,
      if (unreadOnly) 'unread': 1,
    });
    return NotificationPage.fromJson(res.data);
  }

  /// O'qilmaganlar soni (qo'ng'iroq badge'i uchun).
  Future<int> unreadCount() async {
    final res = await _api.dio.get('/notifications/unread-count/');
    return res.data['unread'] ?? 0;
  }

  /// Bildirishnomalarni o'qildi qilish. [ids] berilmasa — hammasini.
  /// Yangilangan o'qilmaganlar sonini qaytaradi.
  Future<int> markRead({List<int>? ids}) async {
    final res = await _api.dio.post('/notifications/read/', data: {
      if (ids != null) 'ids': ids,
    });
    return res.data['unread'] ?? 0;
  }
}
