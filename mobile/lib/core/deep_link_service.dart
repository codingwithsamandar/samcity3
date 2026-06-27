import 'dart:async';

import 'package:app_links/app_links.dart';
import 'package:flutter/foundation.dart';

/// `samcity://payment-success` va boshqa deep link'larni qabul qiladi.
class DeepLinkService {
  DeepLinkService();

  final AppLinks _links = AppLinks();
  StreamSubscription<Uri>? _sub;
  final _controller = StreamController<Uri>.broadcast();

  Stream<Uri> get stream => _controller.stream;

  Future<void> start() async {
    final initial = await _links.getInitialLink();
    if (initial != null) _controller.add(initial);

    _sub = _links.uriLinkStream.listen(
      _controller.add,
      onError: (Object e) => debugPrint('DeepLink error: $e'),
    );
  }

  void dispose() {
    _sub?.cancel();
    _controller.close();
  }
}
