// Do'kon xodimi bilan chat — mobil modellar.

class StoreChatThread {
  final String id;
  final String storeId;
  final String storeName;
  final String customerName;
  final String lastMessage;
  final int unreadCount;
  final DateTime? updatedAt;

  StoreChatThread({
    required this.id,
    required this.storeId,
    required this.storeName,
    required this.customerName,
    this.lastMessage = '',
    this.unreadCount = 0,
    this.updatedAt,
  });

  factory StoreChatThread.fromJson(Map<String, dynamic> j) => StoreChatThread(
        id: j['id'].toString(),
        storeId: j['store_id'].toString(),
        storeName: j['store_name'] ?? '',
        customerName: j['customer_name'] ?? '',
        lastMessage: j['last_message'] ?? '',
        unreadCount: j['unread_count'] ?? 0,
        updatedAt: DateTime.tryParse(j['updated_at'] ?? ''),
      );
}

class StoreChatMessage {
  final String id;
  final String text;
  final String senderId;
  final bool isOwner;
  final DateTime? createdAt;

  StoreChatMessage({
    required this.id,
    required this.text,
    required this.senderId,
    required this.isOwner,
    this.createdAt,
  });

  factory StoreChatMessage.fromJson(Map<String, dynamic> j) => StoreChatMessage(
        id: j['id'].toString(),
        text: j['text'] ?? '',
        senderId: j['sender']?.toString() ?? '',
        isOwner: j['is_owner'] ?? false,
        createdAt: DateTime.tryParse(j['created_at'] ?? ''),
      );

  /// WebSocket'dan kelgan real-time xabar (consumer formati).
  factory StoreChatMessage.fromSocket(Map<String, dynamic> m) => StoreChatMessage(
        id: m['id'].toString(),
        text: m['text'] ?? '',
        senderId: m['sender_id']?.toString() ?? '',
        isOwner: m['is_owner'] ?? false,
        createdAt: DateTime.tryParse(m['created_at'] ?? '') ?? DateTime.now(),
      );
}
