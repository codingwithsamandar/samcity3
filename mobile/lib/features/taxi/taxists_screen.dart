import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import 'taxi_models.dart';

/// Taksistlar ro'yxati (taksi bo'limi).
class TaxistsScreen extends ConsumerStatefulWidget {
  const TaxistsScreen({super.key});

  @override
  ConsumerState<TaxistsScreen> createState() => _TaxistsScreenState();
}

class _TaxistsScreenState extends ConsumerState<TaxistsScreen> {
  late Future<List<Taxist>> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(taxiRepositoryProvider).taxists();
  }

  void _reload() =>
      setState(() => _future = ref.read(taxiRepositoryProvider).taxists());

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Taksi'),
        actions: [
          IconButton(
            tooltip: 'Sayohatlarim',
            onPressed: () => context.push('/trips'),
            icon: const Icon(Icons.history),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<List<Taxist>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: Text("Taksistlarni yuklab bo'lmadi")),
              ]);
            }
            final list = snap.data ?? [];
            if (list.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: Text("Hozircha taksistlar yo'q")),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: list.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _TaxistTile(t: list[i]),
            );
          },
        ),
      ),
    );
  }
}

class _TaxistTile extends StatelessWidget {
  const _TaxistTile({required this.t});
  final Taxist t;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.all(10),
        leading: Stack(
          children: [
            CircleAvatar(
              radius: 26,
              backgroundColor: const Color(0xFF141B29),
              backgroundImage:
                  t.photo != null ? CachedNetworkImageProvider(t.photo!) : null,
              child: t.photo == null ? const Icon(Icons.person) : null,
            ),
            if (t.isOnline)
              Positioned(
                right: 0, bottom: 0,
                child: Container(
                  width: 14, height: 14,
                  decoration: BoxDecoration(
                    color: const Color(0xFF34D399),
                    shape: BoxShape.circle,
                    border: Border.all(color: const Color(0xFF0F1521), width: 2),
                  ),
                ),
              ),
          ],
        ),
        title: Text(t.fullName,
            style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (t.carModel.isNotEmpty) Text(t.carModel),
            Row(children: [
              const Icon(Icons.star, size: 14, color: Color(0xFFCAA23A)),
              const SizedBox(width: 2),
              Text('${t.avgRating} · ${t.tripsCount} sayohat',
                  style: const TextStyle(fontSize: 12)),
            ]),
          ],
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(t.minPriceLabel,
                style: const TextStyle(
                    color: Color(0xFF34D399),
                    fontWeight: FontWeight.w700, fontSize: 12)),
            const Icon(Icons.chevron_right),
          ],
        ),
        onTap: () => context.push('/taxist/${t.id}'),
      ),
    );
  }
}
