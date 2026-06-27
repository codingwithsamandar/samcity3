class AppNotification {
  final int id;
  final String text;
  final String url;
  final String category;
  final String categoryLabel;
  final String icon;
  final bool isRead;
  final DateTime? createdAt;

  AppNotification({
    required this.id,
    required this.text,
    required this.url,
    required this.category,
    required this.categoryLabel,
    required this.icon,
    required this.isRead,
    this.createdAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> j) => AppNotification(
        id: j['id'] is int ? j['id'] : int.tryParse('${j['id']}') ?? 0,
        text: j['text'] ?? '',
        url: j['url'] ?? '',
        category: j['category'] ?? 'system',
        categoryLabel: j['category_label'] ?? '',
        icon: j['icon'] ?? '🔔',
        isRead: j['is_read'] ?? false,
        createdAt: DateTime.tryParse(j['created_at'] ?? ''),
      );
}

class NotificationPage {
  final int count;
  final int unread;
  final List<AppNotification> items;

  NotificationPage({required this.count, required this.unread, required this.items});

  factory NotificationPage.fromJson(Map<String, dynamic> j) => NotificationPage(
        count: j['count'] ?? 0,
        unread: j['unread'] ?? 0,
        items: ((j['results'] as List?) ?? [])
            .map((e) => AppNotification.fromJson(e))
            .toList(),
      );
}
