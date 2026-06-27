import 'package:dio/dio.dart';

import '../api_client.dart';
import '../token_storage.dart';
import 'user.dart';

/// Auth API bilan ishlash: register → OTP → login.
class AuthRepository {
  AuthRepository(this._api, this._storage);

  final ApiClient _api;
  final TokenStorage _storage;

  /// Ro'yxatdan o'tish — OTP yuboradi. DEBUG'da debug_code qaytishi mumkin.
  Future<String?> register({
    required String phone,
    required String name,
    required String password,
  }) async {
    final res = await _api.dio.post('/auth/register/', data: {
      'phone': phone,
      'name': name,
      'password': password,
    });
    return res.data['debug_code'] as String?;
  }

  Future<String?> resendOtp(String phone) async {
    final res = await _api.dio.post('/auth/resend-otp/', data: {'phone': phone});
    return res.data['debug_code'] as String?;
  }

  /// OTP tasdiqlash — JWT qaytaradi va saqlaydi, foydalanuvchini qaytaradi.
  Future<AppUser> verifyOtp({required String phone, required String code}) async {
    final res = await _api.dio.post('/auth/verify-otp/', data: {
      'phone': phone,
      'code': code,
    });
    return _saveAndParse(res.data);
  }

  /// Telefon + parol bilan kirish.
  Future<AppUser> login({required String phone, required String password}) async {
    final res = await _api.dio.post('/auth/login/', data: {
      'phone': phone,
      'password': password,
    });
    return _saveAndParse(res.data);
  }

  Future<AppUser> me() async {
    final res = await _api.dio.get('/auth/me/');
    return AppUser.fromJson(res.data);
  }

  Future<AppUser> updateMe({
    required String name,
    List<int>? avatarBytes,
    String? avatarName,
  }) async {
    final form = FormData.fromMap({
      'name': name,
      if (avatarBytes != null)
        'avatar_upload': MultipartFile.fromBytes(avatarBytes,
            filename: avatarName ?? 'avatar.jpg'),
    });
    final res = await _api.dio.patch('/auth/me/', data: form);
    return AppUser.fromJson(res.data);
  }

  Future<void> logout() => _storage.clear();

  Future<bool> hasSession() async => (await _storage.access) != null;

  Future<AppUser> _saveAndParse(Map<String, dynamic> data) async {
    await _storage.save(
      access: data['access'] as String,
      refresh: data['refresh'] as String,
    );
    return AppUser.fromJson(data['user']);
  }
}
