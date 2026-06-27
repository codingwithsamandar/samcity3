import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';

/// OTP tasdiqlash ekrani. Tasdiqlangach JWT olinadi va asosiy ekranga o'tadi.
class OtpScreen extends ConsumerStatefulWidget {
  const OtpScreen({super.key, required this.phone});
  final String phone;

  @override
  ConsumerState<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends ConsumerState<OtpScreen> {
  final _code = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    setState(() => _loading = true);
    try {
      final user = await ref.read(authRepositoryProvider).verifyOtp(
            phone: widget.phone,
            code: _code.text.trim(),
          );
      ref.read(authControllerProvider.notifier).setUser(user);
      if (mounted) context.go('/');
    } on DioException catch (e) {
      _err(e.response?.data?['detail']?.toString() ?? 'Kod xato');
    } catch (_) {
      _err('Tarmoq xatosi.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _resend() async {
    try {
      await ref.read(authRepositoryProvider).resendOtp(widget.phone);
      _err('Yangi kod yuborildi.', ok: true);
    } catch (_) {
      _err('Qayta yuborib bo\'lmadi.');
    }
  }

  void _err(String m, {bool ok = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(m),
      backgroundColor: ok ? Colors.green.shade700 : Colors.red.shade700,
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Tasdiqlash')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 12),
              Text('${widget.phone} raqamiga yuborilgan 6 xonali kodni kiriting',
                  style: const TextStyle(color: Color(0xFF9AA6BD))),
              const SizedBox(height: 20),
              TextField(
                controller: _code,
                keyboardType: TextInputType.number,
                maxLength: 6,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 24, letterSpacing: 8),
                decoration: const InputDecoration(hintText: '••••••'),
              ),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: _loading ? null : _verify,
                child: _loading
                    ? const SizedBox(
                        height: 20, width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Tasdiqlash'),
              ),
              TextButton(
                onPressed: _resend,
                child: const Text('Kodni qayta yuborish'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
