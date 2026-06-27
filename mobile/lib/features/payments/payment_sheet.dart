import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/providers.dart';
import '../delivery/delivery_models.dart' show money;
import 'payment_repository.dart';

/// To'lov varaqasini ochadi (Payme / Click tugmalari bilan).
Future<void> showPaymentSheet(
  BuildContext context,
  WidgetRef ref, {
  required String targetType,
  required String targetId,
  String title = "To'lov",
}) {
  return showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: const Color(0xFF0F1521),
    builder: (_) => _PaymentSheet(
      targetType: targetType,
      targetId: targetId,
      title: title,
    ),
  );
}

class _PaymentSheet extends ConsumerStatefulWidget {
  const _PaymentSheet({
    required this.targetType,
    required this.targetId,
    required this.title,
  });
  final String targetType;
  final String targetId;
  final String title;

  @override
  ConsumerState<_PaymentSheet> createState() => _PaymentSheetState();
}

class _PaymentSheetState extends ConsumerState<_PaymentSheet> {
  late Future<PaymentLinks> _future;

  @override
  void initState() {
    super.initState();
    _future = ref
        .read(paymentRepositoryProvider)
        .initiate(widget.targetType, widget.targetId);
  }

  Future<void> _open(String url) async {
    final uri = Uri.tryParse(url);
    if (uri == null) return;
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("To'lov sahifasini ochib bo'lmadi")));
      return;
    }
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
              "To'lovdan so'ng ilovaga qayting — holat avtomatik yangilanadi."),
          duration: Duration(seconds: 4),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16, right: 16, top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: FutureBuilder<PaymentLinks>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const SizedBox(
              height: 140,
              child: Center(child: CircularProgressIndicator()),
            );
          }
          if (snap.hasError) {
            final err = snap.error.toString();
            final paid = err.contains('409');
            return SizedBox(
              height: 140,
              child: Center(
                child: Text(paid
                    ? "Bu buyurtma allaqachon to'langan ✅"
                    : "To'lovni boshlab bo'lmadi"),
              ),
            );
          }
          final links = snap.data!;
          return Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(widget.title,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
              const SizedBox(height: 4),
              Text("To'lov summasi: ${money(links.amount)} so'm",
                  style: const TextStyle(color: Color(0xFF9AA6BD))),
              const SizedBox(height: 18),
              _PayButton(
                label: 'Payme orqali to\'lash',
                color: const Color(0xFF33CCCC),
                onTap: () => _open(links.paymeUrl),
              ),
              const SizedBox(height: 10),
              _PayButton(
                label: 'Click orqali to\'lash',
                color: const Color(0xFF0094FF),
                onTap: () => _open(links.clickUrl),
              ),
              const SizedBox(height: 12),
              const Text(
                "To'lovdan so'ng Payme/Click sizni SamCity ilovasiga qaytaradi (samcity://payment-success).",
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 11, color: Color(0xFF69748A)),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _PayButton extends StatelessWidget {
  const _PayButton({required this.label, required this.color, required this.onTap});
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: onTap,
      style: FilledButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.black,
        padding: const EdgeInsets.symmetric(vertical: 14),
      ),
      child: Text(label, style: const TextStyle(fontWeight: FontWeight.w800)),
    );
  }
}
