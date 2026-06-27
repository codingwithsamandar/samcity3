import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../payments/payment_sheet.dart';
import 'taxi_models.dart';

/// Foydalanuvchining taksi sayohatlari tarixi.
class MyTripsScreen extends ConsumerStatefulWidget {
  const MyTripsScreen({super.key});

  @override
  ConsumerState<MyTripsScreen> createState() => _MyTripsScreenState();
}

class _MyTripsScreenState extends ConsumerState<MyTripsScreen> {
  late Future<List<Trip>> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(taxiRepositoryProvider).myTrips();
  }

  void _reload() {
    setState(() => _future = ref.read(taxiRepositoryProvider).myTrips());
  }

  Future<void> _pay(Trip t) async {
    await showPaymentSheet(context, ref,
        targetType: 'trip', targetId: t.id, title: "Sayohat to'lovi");
    _reload();
  }

  Color _statusColor(String s) {
    switch (s) {
      case 'completed':
        return const Color(0xFF34D399);
      case 'cancelled':
        return Colors.red.shade300;
      case 'on_way':
      case 'accepted':
        return const Color(0xFF22D3EE);
      default:
        return const Color(0xFF9AA6BD);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Sayohatlarim')),
      body: FutureBuilder<List<Trip>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return const Center(child: Text("Yuklab bo'lmadi"));
          }
          final trips = snap.data ?? [];
          if (trips.isEmpty) {
            return const Center(child: Text("Hali sayohatlar yo'q"));
          }
          return ListView.separated(
            padding: const EdgeInsets.all(12),
            itemCount: trips.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) {
              final t = trips[i];
              final canPay =
                  t.paymentStatus == 'unpaid' && t.status != 'cancelled';
              return Card(
                child: Column(
                  children: [
                    ListTile(
                      leading: Icon(
                        t.isDelivery ? Icons.local_shipping : Icons.local_taxi,
                        color: const Color(0xFF22D3EE),
                      ),
                      title: Text('${t.pointA} → ${t.pointB}',
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                      subtitle: Text('${t.taxistName} · ${t.priceLabel}'),
                      trailing: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: _statusColor(t.status).withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(t.statusDisplay,
                            style: TextStyle(
                                color: _statusColor(t.status),
                                fontSize: 12, fontWeight: FontWeight.w700)),
                      ),
                    ),
                    if (canPay)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
                        child: SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            onPressed: () => _pay(t),
                            icon: const Icon(Icons.credit_card, size: 18),
                            label: Text("${t.priceLabel} — to'lash"),
                          ),
                        ),
                      ),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }
}
