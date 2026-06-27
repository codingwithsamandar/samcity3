import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import 'delivery_models.dart';

/// Egasi paneli — do'konlarim, do'kon ochish, mahsulot qo'shish.
class MyStoresScreen extends ConsumerStatefulWidget {
  const MyStoresScreen({super.key});

  @override
  ConsumerState<MyStoresScreen> createState() => _MyStoresScreenState();
}

class _MyStoresScreenState extends ConsumerState<MyStoresScreen> {
  Future<(List<Map<String, dynamic>>, List<Store>)>? _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(deliveryRepositoryProvider).myStores();
  }

  void _reload() =>
      setState(() => _future = ref.read(deliveryRepositoryProvider).myStores());

  Future<void> _createStore(List<Map<String, dynamic>> cats) async {
    final name = TextEditingController();
    final desc = TextEditingController();
    final addr = TextEditingController();
    final phone = TextEditingController();
    Object? catId;
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1521),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSt) => Padding(
          padding: EdgeInsets.only(
            left: 16, right: 16, top: 16,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text("Yangi do'kon", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
              const SizedBox(height: 12),
              TextField(controller: name, decoration: const InputDecoration(labelText: "Do'kon nomi *")),
              const SizedBox(height: 10),
              if (cats.isNotEmpty)
                DropdownButtonFormField<Object?>(
                  value: catId,
                  decoration: const InputDecoration(labelText: 'Kategoriya'),
                  items: cats.map((c) => DropdownMenuItem(
                      value: c['id'], child: Text('${c['name']}'))).toList(),
                  onChanged: (v) => setSt(() => catId = v),
                ),
              const SizedBox(height: 10),
              TextField(controller: desc, decoration: const InputDecoration(labelText: 'Tavsif')),
              const SizedBox(height: 10),
              TextField(controller: addr, decoration: const InputDecoration(labelText: 'Manzil')),
              const SizedBox(height: 10),
              TextField(controller: phone, keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(labelText: 'Telefon')),
              const SizedBox(height: 16),
              FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text("Do'kon ochish")),
            ],
          ),
        ),
      ),
    );
    if (ok != true || name.text.trim().isEmpty) return;
    try {
      await ref.read(deliveryRepositoryProvider).createStore({
        'name': name.text.trim(), 'description': desc.text.trim(),
        'address': addr.text.trim(), 'phone': phone.text.trim(),
        if (catId != null) 'category': catId,
      });
      _reload();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Yaratib bo\'lmadi')));
      }
    }
  }

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
            const SnackBar(content: Text('Nom va narx to\'g\'ri kiriting')));
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
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Mahsulot qo\'shildi ✅')));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Qo\'shib bo\'lmadi')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Mening do'konlarim")),
      body: FutureBuilder<(List<Map<String, dynamic>>, List<Store>)>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final cats = snap.data?.$1 ?? [];
          final stores = snap.data?.$2 ?? [];
          return Scaffold(
            floatingActionButton: FloatingActionButton.extended(
              onPressed: () => _createStore(cats),
              icon: const Icon(Icons.add_business),
              label: const Text("Do'kon"),
            ),
            body: stores.isEmpty
                ? ListView(children: const [
                    SizedBox(height: 120),
                    Center(child: Text("Hali do'koningiz yo'q. + tugmasi bilan oching.")),
                  ])
                : ListView.separated(
                    padding: const EdgeInsets.all(12),
                    itemCount: stores.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final s = stores[i];
                      return Card(
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(s.name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                              if (s.category != null)
                                Text(s.category!, style: const TextStyle(color: Color(0xFF9AA6BD), fontSize: 12)),
                              const SizedBox(height: 4),
                              Text('${s.productCount} mahsulot',
                                  style: const TextStyle(color: Color(0xFF69748A), fontSize: 12)),
                              const SizedBox(height: 8),
                              Row(children: [
                                Expanded(
                                  child: FilledButton.icon(
                                    onPressed: () => _addProduct(s),
                                    icon: const Icon(Icons.add, size: 18),
                                    label: const Text('Mahsulot'),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                OutlinedButton(
                                  onPressed: () => context.push('/store/${s.id}'),
                                  child: const Text("Ko'rish"),
                                ),
                              ]),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          );
        },
      ),
    );
  }
}
