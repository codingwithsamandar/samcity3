import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart' hide Provider;

import '../../core/providers.dart';
import '../delivery/delivery_models.dart' show money;
import '../payments/payment_sheet.dart';
import 'service_models.dart';

/// Kommunal / xizmat to'lovlari (elektr, suv, kurs, bog'cha...).
class ServicesScreen extends ConsumerStatefulWidget {
  const ServicesScreen({super.key});

  @override
  ConsumerState<ServicesScreen> createState() => _ServicesScreenState();
}

class _ServicesScreenState extends ConsumerState<ServicesScreen> {
  Future<(List<ProviderCategory>, List<Provider>)>? _future;
  String _cat = '';

  @override
  void initState() {
    super.initState();
    _future = ref.read(servicesRepositoryProvider).providers();
  }

  void _reload() => setState(() => _future = ref
      .read(servicesRepositoryProvider)
      .providers(category: _cat.isEmpty ? null : _cat));

  Future<void> _pay(Provider p) async {
    final amountCtrl = TextEditingController(
        text: p.hasFixedAmount ? p.amount.toString() : '');
    final payerCtrl = TextEditingController();
    final go = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1521),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          left: 16, right: 16, top: 16,
          bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(p.name, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            Text(p.categoryLabel, style: const TextStyle(color: Color(0xFF9AA6BD))),
            const SizedBox(height: 14),
            TextField(
              controller: amountCtrl,
              keyboardType: TextInputType.number,
              enabled: !p.hasFixedAmount,
              decoration: const InputDecoration(labelText: "Summa (so'm) *"),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: payerCtrl,
              decoration: const InputDecoration(
                  labelText: 'Abonent / shartnoma (ixtiyoriy)'),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text("To'lovga o'tish"),
            ),
          ],
        ),
      ),
    );
    if (go != true) return;
    final amount = int.tryParse(amountCtrl.text.replaceAll(' ', '')) ?? 0;
    if (amount <= 0) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text("Summani kiriting")));
      }
      return;
    }
    try {
      final payment = await ref.read(servicesRepositoryProvider).pay(
            providerId: p.id, amount: amount, payerName: payerCtrl.text.trim());
      if (!mounted) return;
      await showPaymentSheet(context, ref,
          targetType: 'service', targetId: payment.id, title: "${p.name} to'lovi");
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Xatolik')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("To'lovlar")),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<(List<ProviderCategory>, List<Provider>)>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            final cats = snap.data?.$1 ?? [];
            final list = snap.data?.$2 ?? [];
            return Column(
              children: [
                SizedBox(
                  height: 48,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                    children: [
                      _chip('Barchasi', ''),
                      ...cats.map((c) => _chip(c.label, c.key)),
                    ],
                  ),
                ),
                Expanded(
                  child: list.isEmpty
                      ? ListView(children: const [
                          SizedBox(height: 120),
                          Center(child: Text("Muassasalar yo'q")),
                        ])
                      : ListView.separated(
                          padding: const EdgeInsets.all(12),
                          itemCount: list.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (_, i) => _providerCard(list[i]),
                        ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _providerCard(Provider p) => Card(
        child: ListTile(
          onTap: () => _pay(p),
          leading: CircleAvatar(
            backgroundColor: const Color(0xFF141B29),
            backgroundImage: p.logo != null ? CachedNetworkImageProvider(p.logo!) : null,
            child: p.logo == null ? const Icon(Icons.receipt_long) : null,
          ),
          title: Text(p.name, style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text(p.categoryLabel +
              (p.hasFixedAmount ? " · ${money(p.amount)} so'm" : ' · erkin summa')),
          trailing: const Icon(Icons.chevron_right),
        ),
      );

  Widget _chip(String label, String key) {
    final sel = _cat == key;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: ChoiceChip(
        label: Text(label),
        selected: sel,
        onSelected: (_) {
          _cat = key;
          _reload();
        },
      ),
    );
  }
}
