import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

import 'config.dart';
import 'token_storage.dart';

/// Umumiy kuzatuv WebSocket — buyurtma/sayohat holatini jonli oladi.
/// Django consumer'lari (ws/delivery/track/<id>/, ws/taxi/track/<id>/) bilan
/// ishlaydi; JWT token query orqali yuboriladi (ws_auth.py).
///
/// Server xabarlari: {type:'snapshot'|'status', status, status_display, ...}.
class TrackSocket {
  TrackSocket(this._storage, this._path);
  final TokenStorage _storage;
  final String _path; // masalan: 'delivery/track/<orderId>' yoki 'taxi/track/<tripId>'

  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  final _events = StreamController<Map<String, dynamic>>.broadcast();

  /// Dekodlangan WS xabarlari oqimi (status/snapshot/location).
  Stream<Map<String, dynamic>> get events => _events.stream;

  Future<void> connect() async {
    final token = await _storage.access;
    if (token == null) return;
    final url = '${AppConfig.wsBase}/ws/$_path/?token=$token';
    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      _sub = _channel!.stream.listen(_onData, onError: (_) {}, onDone: () {});
    } catch (_) {/* WS bo'lmasa — REST/pull-to-refresh baribir ishlaydi */}
  }

  void _onData(dynamic raw) {
    try {
      final data = jsonDecode(raw as String) as Map<String, dynamic>;
      _events.add(data);
    } catch (_) {}
  }

  void dispose() {
    _sub?.cancel();
    _channel?.sink.close();
    _events.close();
  }
}
