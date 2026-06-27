import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';

/// Kirish / Ro'yxatdan o'tish ekrani (telefon + parol).
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  bool _isRegister = false;
  bool _loading = false;
  final _phone = TextEditingController();
  final _name = TextEditingController();
  final _password = TextEditingController();

  @override
  void dispose() {
    _phone.dispose();
    _name.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _loading = true);
    final repo = ref.read(authRepositoryProvider);
    try {
      if (_isRegister) {
        await repo.register(
          phone: _phone.text,
          name: _name.text,
          password: _password.text,
        );
        if (mounted) context.push('/otp', extra: _phone.text);
      } else {
        final user = await repo.login(
          phone: _phone.text,
          password: _password.text,
        );
        ref.read(authControllerProvider.notifier).setUser(user);
        if (mounted) context.go('/');
      }
    } on DioException catch (e) {
      _showError(e.response?.data?['detail']?.toString() ?? 'Xatolik yuz berdi');
    } catch (_) {
      _showError('Tarmoq xatosi. Internetni tekshiring.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showError(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: Colors.red.shade700),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(Icons.location_on, size: 56, color: Color(0xFF34D399)),
                const SizedBox(height: 12),
                Text('SamCity',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(_isRegister ? "Ro'yxatdan o'tish" : 'Hisobingizga kiring',
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Color(0xFF9AA6BD))),
                const SizedBox(height: 28),
                TextField(
                  controller: _phone,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(
                    labelText: 'Telefon', hintText: '+998 ...'),
                ),
                if (_isRegister) ...[
                  const SizedBox(height: 12),
                  TextField(
                    controller: _name,
                    decoration: const InputDecoration(labelText: 'Ism'),
                  ),
                ],
                const SizedBox(height: 12),
                TextField(
                  controller: _password,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Parol'),
                ),
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: _loading ? null : _submit,
                  child: _loading
                      ? const SizedBox(
                          height: 20, width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2))
                      : Text(_isRegister ? "Ro'yxatdan o'tish" : 'Kirish'),
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: () => setState(() => _isRegister = !_isRegister),
                  child: Text(_isRegister
                      ? 'Hisobingiz bormi? Kirish'
                      : "Hisob yo'qmi? Ro'yxatdan o'tish"),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
