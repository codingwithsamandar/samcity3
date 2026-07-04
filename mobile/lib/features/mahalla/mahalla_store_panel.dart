import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../delivery/delivery_models.dart';

/// Mahalla do'koni egasi (boshlig'i) paneli — o'z do'konlari, mahsulotlar va
/// olib ketish buyurtmalarini boshqarish.
class MahallaStorePanel extends ConsumerStatefulWidget {
  const MahallaStorePanel({super.key, required this.neighborhoodId});
  final String neighborhoodId;

  @override
  ConsumerState<MahallaStorePanel> createState() => _MahallaStorePanelState();
}

class _MahallaStorePanelState extends ConsumerState<MahallaStorePanel> {
  Future<(List<Map<String, dynamic>>, List<Store>)>? _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(deliveryRepositoryProvider).myStores();
  }

  void _reload() =>
      setState(() => _future = ref.read(deliveryRepositoryProvider).myStores());

  Future<void> _addProduct(Store s) async {
    final name = TextEditingController();
    final price = TextEditingController();
    final stock = TextEditingController(text: '10');
    final desc = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
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
            Text("Mahsulot — ${s.name}", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            TextField(controller: name, decoration: const InputDecoration(labelText: 'Nomi *')),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: TextField(controller: price, keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: "Narx (so'm) *"))),
              const SizedBox(width: 10),
              Expanded(child: TextField(controller: stock, keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Zaxira'))),
            ]),
            const SizedBox(height: 10),
            TextField(controller: desc, decoration: const InputDecoration(labelText: 'Tavsif')),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text("Qo'shish")),
          ],
        ),
      ),
    );
    if (ok != true) return;
    if (name.text.trim().isEmpty || (int.tryParse(price.text.replaceAll(' ', '')) ?? 0) <= 0) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Nom va narxni to\'g\'ri kiriting')));
      }
      return;
    }
    try {
      await ref.read(deliveryRepositoryProvider).addProduct(s.id, {
        'name': name.text.trim(),
        'price': price.text.replaceAll(' ', ''),
        'stock': stock.text.trim(),
        'description': desc.text.trim(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Mahsulot qo\'shildi ✅')));
        _reload();
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Qo\'shib bo\'lmadi')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Do'kon egasi paneli")),
      body: FutureBuilder<(List<Map<String, dynamic>>, List<Store>)>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final all = snap.data?.$2 ?? [];
          final mahalla = all.where((s) => s.isMahalla).toList();
          if (mahalla.isEmpty) {
            return ListView(padding: const EdgeInsets.all(20), children: const [
              SizedBox(height: 60),
              Icon(Icons.storefront_outlined, size: 56, color: Color(0xFF69748A)),
              SizedBox(height: 16),
              Text("Sizda mahalla do'koni yo'q",
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
              SizedBox(height: 8),
              Text(
                "Do'kon ochish uchun «Do'kon ochish» tugmasi orqali ariza bering. "
                "Mahalla admini tasdiqlagach do'koningiz shu yerda ko'rinadi.",
                textAlign: TextAlign.center,
                style: TextStyle(color: Color(0xFF9AA6BD), height: 1.5),
              ),
            ]);
          }
          return RefreshIndicator(
            onRefresh: () async => _reload(),
            child: ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: mahalla.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _storeCard(mahalla[i]),
            ),
          );
        },
      ),
    );
  }

  Widget _storeCard(Store s) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Text('🛒', style: TextStyle(fontSize: 22)),
              const SizedBox(width: 8),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(s.name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                  Text('${s.productCount} mahsulot',
                      style: const TextStyle(color: Color(0xFF69748A), fontSize: 12)),
                ]),
              ),
              if (s.pickupEnabled)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                      color: const Color(0x2234D399), borderRadius: BorderRadius.circular(8)),
                  child: const Text('Olib ketish',
                      style: TextStyle(fontSize: 10, color: Color(0xFF34D399), fontWeight: FontWeight.w700)),
                ),
            ]),
            const SizedBox(height: 12),
            Row(children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: () => _addProduct(s),
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Mahsulot'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => _StoreOrdersPage(storeName: s.name))),
                  icon: const Icon(Icons.receipt_long_outlined, size: 18),
                  label: const Text('Buyurtmalar'),
                ),
              ),
            ]),
          ],
        ),
      ),
    );
  }
}

/// Do'kon egasiga kelgan olib ketish buyurtmalari — holatni boshqarish bilan.
class _StoreOrdersPage extends ConsumerStatefulWidget {
  const _StoreOrdersPage({required this.storeName});
  final String storeName;
  @override
  ConsumerState<_StoreOrdersPage> createState() => _StoreOrdersPageState();
}

class _StoreOrdersPageState extends ConsumerState<_StoreOrdersPage> {
  bool _loading = true;
  List<DeliveryOrder> _orders = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final items = await ref.read(deliveryRepositoryProvider).storeOrders(fulfillment: 'pickup');
      if (mounted) setState(() { _orders = items; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _setStatus(DeliveryOrder o, String status) async {
    try {
      final updated = await ref.read(deliveryRepositoryProvider).setStoreOrderStatus(o.id, status);
      setState(() => _orders = _orders.map((x) => x.id == updated.id ? updated : x).toList());
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Holatni o\'zgartirib bo\'lmadi')));
      }
    }
  }

  /// Joriy holatga qarab keyingi amal tugmalari.
  List<Widget> _actions(DeliveryOrder o) {
    switch (o.status) {
      case 'pending':
        return [
          _btn('Qabul qilish', () => _setStatus(o, 'accepted')),
          _btn('Bekor', () => _setStatus(o, 'cancelled'), danger: true),
        ];
      case 'accepted':
        return [
          _btn("Yig'ishni boshlash", () => _setStatus(o, 'preparing')),
          _btn('Bekor', () => _setStatus(o, 'cancelled'), danger: true),
        ];
      case 'preparing':
        return [_btn('Tayyor', () => _setStatus(o, 'ready'))];
      case 'ready':
        return [const Text('Mijoz olib ketishini kutmoqda',
            style: TextStyle(color: Color(0xFF34D399), fontWeight: FontWeight.w600))];
      default:
        return [];
    }
  }

  Widget _btn(String label, VoidCallback onTap, {bool danger = false}) => Padding(
        padding: const EdgeInsets.only(right: 8),
        child: danger
            ? OutlinedButton(
                onPressed: onTap,
                style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFFB7185)),
                child: Text(label))
            : FilledButton(onPressed: onTap, child: Text(label)),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Buyurtmalar')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _orders.isEmpty
              ? ListView(children: const [
                  SizedBox(height: 120),
                  Center(child: Text('Hozircha buyurtma yo\'q')),
                ])
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(12),
                    itemCount: _orders.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (_, i) => _orderCard(_orders[i]),
                  ),
                ),
    );
  }

  Widget _orderCard(DeliveryOrder o) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Text('#${o.id.substring(0, o.id.length > 8 ? 8 : o.id.length)}',
                  style: const TextStyle(fontWeight: FontWeight.w800)),
            ),
            Chip(label: Text(o.label, style: const TextStyle(fontSize: 11))),
          ]),
          const SizedBox(height: 6),
          ...o.items.map((it) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Text('${it.quantity}× ${it.productName}',
                    style: const TextStyle(color: Color(0xFF9AA6BD), fontSize: 13)),
              )),
          const SizedBox(height: 6),
          Row(children: [
            Text("${money(o.total)} so'm", style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(width: 8),
            Text(o.isPaid ? "To'langan" : "To'lanmagan",
                style: TextStyle(
                    fontSize: 11,
                    color: o.isPaid ? const Color(0xFF34D399) : const Color(0xFFFB7185))),
          ]),
          const SizedBox(height: 10),
          Wrap(spacing: 0, runSpacing: 8, children: _actions(o)),
        ]),
      ),
    );
  }
}
