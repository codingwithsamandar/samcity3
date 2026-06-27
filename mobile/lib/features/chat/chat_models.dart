class ChatRoom {
  final String id;
  final String name;
  final String description;
  final int memberCount;
  final String? lastMessageText;
  final DateTime? lastMessageTime;
  final String myStatus; // approved | pending | banned | none | guest

  ChatRoom({
    required this.id,
    required this.name,
    required this.description,
    required this.memberCount,
    this.lastMessageText,
    this.lastMessageTime,
    required this.myStatus,
  });

  factory ChatRoom.fromJson(Map<String, dynamic> j) {
    final lm = j['last_message'];
    return ChatRoom(
      id: j['id'].toString(),
      name: j['name'] ?? '',
      description: j['description'] ?? '',
      memberCount: j['member_count'] ?? 0,
      lastMessageText: lm?['text'],
      lastMessageTime:
          lm != null ? DateTime.tryParse(lm['created_at'] ?? '') : null,
      myStatus: j['my_status'] ?? 'none',
    );
  }
}

class ChatMessage {
  final String id;
  final String text;
  final String? image;
  final String userId;
  final String userName;
  final String? userAvatar;
  final bool isAdminMessage;
  final String? replyToText;
  final String? replyToUser;
  final DateTime? createdAt;

  ChatMessage({
    required this.id,
    required this.text,
    this.image,
    required this.userId,
    required this.userName,
    this.userAvatar,
    required this.isAdminMessage,
    this.replyToText,
    this.replyToUser,
    this.createdAt,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> j) {
    final reply = j['reply_to'];
    return ChatMessage(
      id: j['id'].toString(),
      text: j['text'] ?? '',
      image: j['image'],
      userId: j['user']?['id']?.toString() ?? '',
      userName: j['user']?['name'] ?? '',
      userAvatar: j['user']?['avatar'],
      isAdminMessage: j['is_admin_message'] ?? false,
      replyToText: reply?['text'],
      replyToUser: reply?['user'],
      createdAt: DateTime.tryParse(j['created_at'] ?? ''),
    );
  }

  /// WebSocket'dan kelgan real-time xabar (consumer formati).
  factory ChatMessage.fromSocket(Map<String, dynamic> m) {
    final reply = m['reply'];
    return ChatMessage(
      id: m['id'].toString(),
      text: m['text'] ?? '',
      image: m['image_url'],
      userId: m['real_user_id']?.toString() ?? '',
      userName: m['user_name'] ?? '',
      userAvatar: null,
      isAdminMessage: m['is_admin'] ?? false,
      replyToText: reply?['text'],
      replyToUser: reply?['author'],
      createdAt: DateTime.now(),
    );
  }
}

class ChatHistory {
  final List<ChatMessage> messages;
  final bool canWrite;
  final String myStatus;
  final int count;

  ChatHistory({
    required this.messages,
    required this.canWrite,
    required this.myStatus,
    required this.count,
  });

  factory ChatHistory.fromJson(Map<String, dynamic> j) => ChatHistory(
        messages: ((j['results'] as List?) ?? [])
            .map((e) => ChatMessage.fromJson(e))
            .toList(),
        canWrite: j['can_write'] ?? false,
        myStatus: j['my_status'] ?? 'pending',
        count: j['count'] ?? 0,
      );
}
