import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../../core/config.dart';
import '../../core/token_storage.dart';
import 'store_chat_models.dart';

/// Bitta do'kon-chat threadi uchun real-time WebSocket ulanishi.
/// Django `StoreChatConsumer` (ws/delivery/chat/<thread_id>/) bilan ishlaydi.
class StoreChatSocket {
  StoreChatSocket(this._storage);
  final TokenStorage _storage;

  WebSocketChannel? _channel;
  StreamSubscription? _sub;

  final _messages = StreamController<StoreChatMessage>.broadcast();
  final _connected = StreamController<bool>.broadcast();

  Stream<StoreChatMessage> get messages => _messages.stream;
  Stream<bool> get connected => _connected.stream;

  bool _open = false;
  bool get isOpen => _open;

  Future<bool> connect(String threadId) async {
    final token = await _storage.access;
    if (token == null) return false;
    final url = '${AppConfig.wsBase}/ws/delivery/chat/$threadId/?token=$token';
    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      _sub = _channel!.stream.listen(
        _onData,
        onError: (_) { _open = false; _connected.add(false); },
        onDone: () { _open = false; _connected.add(false); },
      );
      _open = true;
      _connected.add(true);
      return true;
    } catch (_) {
      _open = false;
      _connected.add(false);
      return false;
    }
  }

  void _onData(dynamic raw) {
    try {
      final data = jsonDecode(raw as String) as Map<String, dynamic>;
      if (data['type'] == 'message') {
        _messages.add(StoreChatMessage.fromSocket(data));
      }
    } catch (_) {/* boshqa hodisalarni e'tiborsiz qoldiramiz */}
  }

  void send(String text) {
    final ch = _channel;
    if (ch == null || !_open) return;
    ch.sink.add(jsonEncode({'type': 'message', 'text': text}));
  }

  void dispose() {
    _sub?.cancel();
    _channel?.sink.close();
    _messages.close();
    _connected.close();
  }
}
