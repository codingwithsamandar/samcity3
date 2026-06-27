import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../payments/payment_sheet.dart';
import 'booking_models.dart';

/// Foydalanuvchining joy bronlari.
class MyBookingsScreen extends ConsumerStatefulWidget {
  const MyBookingsScreen({super.key});

  @override
  ConsumerState<MyBookingsScreen> createState() => _MyBookingsScreenState();
}

class _MyBookingsScreenState extends ConsumerState<MyBookingsScreen> {
  late Future<List<VenueBooking>> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(bookingRepositoryProvider).myBookings();
  }

  void _reload() =>
      setState(() => _future = ref.read(bookingRepositoryProvider).myBookings());

  Color _statusColor(String s) {
    switch (s) {
      case 'confirmed':
        return const Color(0xFF34D399);
      case 'cancelled':
        return Colors.red.shade300;
      case 'completed':
        return const Color(0xFF9AA6BD);
      default:
        return const Color(0xFFCAA23A);
    }
  }

  Future<void> _cancel(VenueBooking b) async {
    try {
      await ref.read(bookingRepositoryProvider).cancel(b.id);
      _reload();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Bekor qilib bo\'lmadi')));
      }
    }
  }

  Future<void> _pay(VenueBooking b) async {
    await showPaymentSheet(context, ref,
        targetType: 'booking', targetId: b.id, title: "Bron to'lovi");
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Bronlarim')),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<List<VenueBooking>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: Text("Yuklab bo'lmadi")),
              ]);
            }
            final list = snap.data ?? [];
            if (list.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: Text("Hali bronlar yo'q")),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: list.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final b = list[i];
                final canCancel =
                    b.status != 'cancelled' && b.status != 'completed';
                final canPay = b.status == 'pending';
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(b.venueName,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w700, fontSize: 16)),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: _statusColor(b.status).withOpacity(0.15),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(b.statusDisplay,
                                  style: TextStyle(
                                      color: _statusColor(b.status),
                                      fontSize: 12,
                                      fontWeight: FontWeight.w700)),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Row(children: [
                          const Icon(Icons.calendar_today,
                              size: 15, color: Color(0xFF9AA6BD)),
                          const SizedBox(width: 6),
                          Text(b.bookingDate),
                          const SizedBox(width: 16),
                          const Icon(Icons.groups,
                              size: 15, color: Color(0xFF9AA6BD)),
                          const SizedBox(width: 6),
                          Text('${b.guests}'),
                        ]),
                        const SizedBox(height: 4),
                        Text(b.amountLabel,
                            style: const TextStyle(
                                color: Color(0xFF34D399),
                                fontWeight: FontWeight.w700)),
                        if (canPay) ...[
                          const SizedBox(height: 8),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton.icon(
                              onPressed: () => _pay(b),
                              icon: const Icon(Icons.credit_card, size: 18),
                              label: Text("${b.amountLabel} — to'lash"),
                            ),
                          ),
                        ],
                        if (canCancel)
                          Align(
                            alignment: Alignment.centerRight,
                            child: TextButton.icon(
                              onPressed: () => _cancel(b),
                              icon: const Icon(Icons.close, size: 16),
                              label: const Text('Bekor qilish'),
                              style: TextButton.styleFrom(
                                  foregroundColor: Colors.red.shade300),
                            ),
                          ),
                      ],
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
