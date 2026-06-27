import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import '../../core/config.dart';
import '../../core/token_storage.dart';

/// Bildirishnoma WebSocket — o'qilmaganlar sonini jonli yetkazadi.
/// Ulanish uzilsa 5 soniyadan keyin qayta ulanadi.
class NotifSocket {
  NotifSocket(this._storage);
  final TokenStorage _storage;

  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  Timer? _reconnectTimer;
  bool _disposed = false;
  final _unread = StreamController<int>.broadcast();

  Stream<int> get unread => _unread.stream;

  Future<void> connect() async {
    if (_disposed) return;
    _reconnectTimer?.cancel();
    await _sub?.cancel();
    await _channel?.sink.close();

    final token = await _storage.access;
    if (token == null) return;

    final url = '${AppConfig.wsBase}/ws/notifications/?token=$token';
    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      _sub = _channel!.stream.listen(
        _onData,
        onError: (_) => _scheduleReconnect(),
        onDone: _scheduleReconnect,
        cancelOnError: true,
      );
    } catch (_) {
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_disposed) return;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 5), connect);
  }

  void _onData(dynamic raw) {
    try {
      final data = jsonDecode(raw as String) as Map<String, dynamic>;
      final type = data['type'];
      if (type == 'unread' || type == 'notification') {
        final count = data['count'];
        if (count is int) _unread.add(count);
      }
    } catch (_) {}
  }

  void dispose() {
    _disposed = true;
    _reconnectTimer?.cancel();
    _sub?.cancel();
    _channel?.sink.close();
    _unread.close();
  }
}
