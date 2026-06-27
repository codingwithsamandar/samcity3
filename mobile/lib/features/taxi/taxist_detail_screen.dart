import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import 'taxi_models.dart';

/// Taksist detali — marshrutlar va buyurtma berish.
class TaxistDetailScreen extends ConsumerStatefulWidget {
  const TaxistDetailScreen({super.key, required this.id});
  final String id;

  @override
  ConsumerState<TaxistDetailScreen> createState() => _TaxistDetailScreenState();
}

class _TaxistDetailScreenState extends ConsumerState<TaxistDetailScreen> {
  late Future<TaxistDetail> _future;
  bool _booking = false;

  @override
  void initState() {
    super.initState();
    _future = ref.read(taxiRepositoryProvider).taxistDetail(widget.id);
  }

  Future<void> _book(TaxiRoute route, bool isDelivery) async {
    setState(() => _booking = true);
    try {
      await ref.read(taxiRepositoryProvider)
          .book(routeId: route.id, isDelivery: isDelivery);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: const Text('Buyurtma qabul qilindi! ✅'),
          backgroundColor: Colors.green.shade700,
        ));
        context.push('/trips');
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Buyurtma berilmadi')));
      }
    } finally {
      if (mounted) setState(() => _booking = false);
    }
  }

  void _confirm(TaxiRoute r) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF0F1521),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('${r.pointA} → ${r.pointB}',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _booking ? null : () { Navigator.pop(context); _book(r, false); },
              icon: const Icon(Icons.person),
              label: Text("Yo'lovchi — ${r.passengerPrice} so'm"),
            ),
            if (r.deliveryPrice != null) ...[
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: _booking ? null : () { Navigator.pop(context); _book(r, true); },
                icon: const Icon(Icons.local_shipping),
                label: Text("Dostavka — ${r.deliveryPrice} so'm"),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Taksist')),
      body: FutureBuilder<TaxistDetail>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return const Center(child: Text("Yuklab bo'lmadi"));
          }
          final d = snap.data!;
          final t = d.taxist;
          return ListView(
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    CircleAvatar(
                      radius: 40,
                      backgroundColor: const Color(0xFF141B29),
                      backgroundImage: t.photo != null
                          ? CachedNetworkImageProvider(t.photo!)
                          : null,
                      child: t.photo == null
                          ? const Icon(Icons.person, size: 40)
                          : null,
                    ),
                    const SizedBox(height: 10),
                    Text(t.fullName,
                        style: const TextStyle(
                            fontSize: 20, fontWeight: FontWeight.w800)),
                    if (d.carFullName != null)
                      Text('${d.carFullName} · ${d.carPlate ?? ''}',
                          style: const TextStyle(color: Color(0xFF9AA6BD))),
                    const SizedBox(height: 6),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.star, size: 16, color: Color(0xFFCAA23A)),
                        const SizedBox(width: 2),
                        Text('${t.avgRating} (${t.reviewCount})  ·  '
                            '${t.tripsCount} sayohat'),
                      ],
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              const Padding(
                padding: EdgeInsets.fromLTRB(16, 16, 16, 6),
                child: Text('Marshrutlar',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
              ),
              if (d.routes.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(24),
                  child: Center(child: Text("Marshrutlar yo'q")),
                )
              else
                ...d.routes.map((r) => Card(
                      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                      child: ListTile(
                        title: Text('${r.pointA} → ${r.pointB}'),
                        subtitle: Text("Yo'lovchi: ${r.passengerPrice} so'm"
                            "${r.deliveryPrice != null ? ' · Dostavka: ${r.deliveryPrice} so\'m' : ''}"),
                        trailing: FilledButton(
                          onPressed: () => _confirm(r),
                          child: const Text('Buyurtma'),
                        ),
                      ),
                    )),
              const SizedBox(height: 24),
            ],
          );
        },
      ),
    );
  }
}
