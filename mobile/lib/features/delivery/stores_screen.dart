import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import 'delivery_models.dart';

/// Do'konlar ro'yxati (yetkazish bo'limi).
class StoresScreen extends ConsumerStatefulWidget {
  const StoresScreen({super.key});

  @override
  ConsumerState<StoresScreen> createState() => _StoresScreenState();
}

class _StoresScreenState extends ConsumerState<StoresScreen> {
  late Future<List<Store>> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(deliveryRepositoryProvider).stores();
  }

  void _reload() => setState(
      () => _future = ref.read(deliveryRepositoryProvider).stores());

  @override
  Widget build(BuildContext context) {
    final cartQty = ref.watch(cartControllerProvider).totalQuantity;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Yetkazish'),
        actions: [
          IconButton(
            tooltip: 'Buyurtmalarim',
            onPressed: () => context.push('/orders'),
            icon: const Icon(Icons.receipt_long_outlined),
          ),
          IconButton(
            tooltip: 'Savat',
            onPressed: () => context.push('/cart'),
            icon: Badge(
              isLabelVisible: cartQty > 0,
              label: Text('$cartQty'),
              child: const Icon(Icons.shopping_cart_outlined),
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<List<Store>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: Text("Do'konlarni yuklab bo'lmadi")),
              ]);
            }
            final stores = snap.data ?? [];
            if (stores.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: Text("Hozircha do'konlar yo'q")),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: stores.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _StoreTile(store: stores[i]),
            );
          },
        ),
      ),
    );
  }
}

class _StoreTile extends StatelessWidget {
  const _StoreTile({required this.store});
  final Store store;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.all(10),
        leading: ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: SizedBox(
            width: 56,
            height: 56,
            child: store.logo != null
                ? CachedNetworkImage(imageUrl: store.logo!, fit: BoxFit.cover)
                : Container(
                    color: const Color(0xFF141B29),
                    child: const Icon(Icons.storefront, color: Color(0xFF69748A)),
                  ),
          ),
        ),
        title: Text(store.name,
            style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text(
          store.address.isNotEmpty ? store.address : '${store.productCount} mahsulot',
          maxLines: 1, overflow: TextOverflow.ellipsis,
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push('/store/${store.id}'),
      ),
    );
  }
}
