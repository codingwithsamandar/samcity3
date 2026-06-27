import 'package:dio/dio.dart';

import 'config.dart';
import 'token_storage.dart';

/// Dio asosidagi API klient.
/// - Har so'rovga JWT access tokenni qo'shadi.
/// - 401 bo'lsa refresh token bilan access'ni yangilab, so'rovni qayta yuboradi.
class ApiClient {
  ApiClient(this._storage) {
    _dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiBase,
      connectTimeout: const Duration(seconds: 15),
      receiveTimeout: const Duration(seconds: 20),
    ));
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.access;
        if (token != null && options.headers['Authorization'] == null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (e, handler) async {
        if (e.response?.statusCode == 401 && !_isRefreshCall(e)) {
          final refreshed = await _tryRefresh();
          if (refreshed) {
            final req = e.requestOptions;
            final newToken = await _storage.access;
            req.headers['Authorization'] = 'Bearer $newToken';
            try {
              final clone = await _dio.fetch(req);
              return handler.resolve(clone);
            } catch (_) {/* tushib qolsa quyiga */}
          }
        }
        handler.next(e);
      },
    ));
  }

  late final Dio _dio;
  final TokenStorage _storage;

  Dio get dio => _dio;

  bool _isRefreshCall(DioException e) =>
      e.requestOptions.path.contains('/auth/refresh');

  Future<bool> _tryRefresh() async {
    final refresh = await _storage.refresh;
    if (refresh == null) return false;
    try {
      final res = await Dio(BaseOptions(baseUrl: AppConfig.apiBase))
          .post('/auth/refresh/', data: {'refresh': refresh});
      final access = res.data['access'] as String?;
      if (access != null) {
        await _storage.updateAccess(access);
        return true;
      }
    } catch (_) {}
    return false;
  }
}
