import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'delivery_models.dart';

/// Do'kon detali + mahsulotlar (savatga qo'shish bilan).
class StoreDetailScreen extends ConsumerStatefulWidget {
  const StoreDetailScreen({super.key, required this.id});
  final String id;

  @override
  ConsumerState<StoreDetailScreen> createState() => _StoreDetailScreenState();
}

class _StoreDetailScreenState extends ConsumerState<StoreDetailScreen> {
  late Future<StoreDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(deliveryRepositoryProvider).storeDetail(widget.id);
  }

  Future<void> _add(Product p) async {
    try {
      await ref.read(cartControllerProvider.notifier).add(p.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text("«${p.name}» savatga qo'shildi"),
          backgroundColor: Colors.green.shade700,
          duration: const Duration(milliseconds: 900),
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(_msg(e)), backgroundColor: Colors.orange.shade800));
      }
    }
  }

  String _msg(Object e) {
    final s = e.toString();
    return s.contains('409') ? 'Omborda yetarli mavjud emas' : 'Xatolik yuz berdi';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Do'kon")),
      body: FutureBuilder<StoreDetail>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return const Center(child: Text("Do'konni yuklab bo'lmadi"));
          }
          final d = snap.data!;
          return ListView(
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(14),
                    child: SizedBox(
                      width: 64, height: 64,
                      child: d.store.logo != null
                          ? CachedNetworkImage(
                              imageUrl: d.store.logo!, fit: BoxFit.cover)
                          : Container(
                              color: const Color(0xFF141B29),
                              child: const Icon(Icons.storefront)),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(d.store.name,
                            style: const TextStyle(
                                fontSize: 18, fontWeight: FontWeight.w800)),
                        if (d.store.address.isNotEmpty)
                          Text(d.store.address,
                              style: const TextStyle(color: Color(0xFF9AA6BD))),
                      ],
                    ),
                  ),
                ]),
              ),
              const Divider(height: 1),
              if (d.products.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(40),
                  child: Center(child: Text("Mahsulotlar yo'q")),
                )
              else
                ...d.products.map((p) => _ProductTile(product: p, onAdd: () => _add(p))),
              const SizedBox(height: 24),
            ],
          );
        },
      ),
    );
  }
}

class _ProductTile extends StatelessWidget {
  const _ProductTile({required this.product, required this.onAdd});
  final Product product;
  final VoidCallback onAdd;

  @override
  Widget build(BuildContext context) {
    final out = product.stock <= 0;
    return ListTile(
      leading: ClipRRect(
        borderRadius: BorderRadius.circular(10),
        child: SizedBox(
          width: 52, height: 52,
          child: product.cover != null
              ? CachedNetworkImage(imageUrl: product.cover!, fit: BoxFit.cover)
              : Container(
                  color: const Color(0xFF141B29),
                  child: const Icon(Icons.fastfood, color: Color(0xFF69748A))),
        ),
      ),
      title: Text(product.name),
      subtitle: Text(out ? 'Omborda yo\'q' : product.priceLabel,
          style: TextStyle(
              color: out ? Colors.red.shade300 : const Color(0xFF34D399),
              fontWeight: FontWeight.w700)),
      trailing: FilledButton(
        onPressed: out ? null : onAdd,
        style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8)),
        child: const Icon(Icons.add, size: 20),
      ),
    );
  }
}
