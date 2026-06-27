import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../../core/config.dart';
import '../../core/token_storage.dart';
import 'chat_models.dart';

/// Bitta chat xonasi uchun real-time WebSocket ulanishi.
/// Mavjud Django `ChatConsumer` (ws/chat/<id>/) bilan ishlaydi, JWT token bilan.
class ChatSocket {
  ChatSocket(this._storage);
  final TokenStorage _storage;

  WebSocketChannel? _channel;
  StreamSubscription? _sub;

  final _messages = StreamController<ChatMessage>.broadcast();
  final _canWrite = StreamController<bool>.broadcast();
  final _connected = StreamController<bool>.broadcast();

  Stream<ChatMessage> get messages => _messages.stream;
  Stream<bool> get canWrite => _canWrite.stream;
  Stream<bool> get connected => _connected.stream;

  Future<bool> connect(String roomId) async {
    final token = await _storage.access;
    if (token == null) return false;
    final url = '${AppConfig.wsBase}/ws/chat/$roomId/?token=$token';
    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      _sub = _channel!.stream.listen(
        _onData,
        onError: (_) => _connected.add(false),
        onDone: () => _connected.add(false),
      );
      _connected.add(true);
      return true;
    } catch (_) {
      _connected.add(false);
      return false;
    }
  }

  void _onData(dynamic raw) {
    try {
      final data = jsonDecode(raw as String) as Map<String, dynamic>;
      switch (data['type']) {
        case 'status':
          // Server javob berdi — ulanish haqiqatan tirik.
          _connected.add(true);
          final canWrite =
              (data['is_admin'] == true) || (data['is_approved'] == true);
          _canWrite.add(canWrite);
          break;
        case 'message':
          _messages.add(ChatMessage.fromSocket(data));
          break;
        case 'banned':
          _canWrite.add(false);
          break;
      }
    } catch (_) {/* boshqa hodisa turlarini e'tiborsiz qoldiramiz */}
  }

  void send(String text) {
    final ch = _channel;
    if (ch == null) return;
    ch.sink.add(jsonEncode({'type': 'message', 'text': text}));
  }

  void dispose() {
    _sub?.cancel();
    _channel?.sink.close();
    _messages.close();
    _canWrite.close();
    _connected.close();
  }
}
