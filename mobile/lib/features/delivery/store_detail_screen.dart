import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../store_chat/store_chat_screen.dart';
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
  bool? _subscribed;

  @override
  void initState() {
    super.initState();
    _future = ref.read(deliveryRepositoryProvider).storeDetail(widget.id);
  }

  Future<void> _toggleSubscribe() async {
    try {
      final on = await ref.read(deliveryRepositoryProvider).toggleSubscription(widget.id);
      if (mounted) setState(() => _subscribed = on);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Xatolik yuz berdi')));
      }
    }
  }

  Future<void> _contactStore() async {
    try {
      final thread = await ref.read(storeChatRepositoryProvider).start(widget.id);
      if (!mounted) return;
      Navigator.of(context).push(MaterialPageRoute(
        builder: (_) => StoreChatScreen(threadId: thread.id, title: thread.storeName),
      ));
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Suhbatni ochib bo\'lmadi')));
      }
    }
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
      appBar: AppBar(
        title: const Text("Do'kon"),
        actions: [
          IconButton(
            tooltip: "Do'kon bilan bog'lanish",
            onPressed: _contactStore,
            icon: const Icon(Icons.chat_bubble_outline),
          ),
        ],
      ),
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
                        if (d.store.workingHours.isNotEmpty)
                          Text('🕒 ${d.store.workingHours}',
                              style: const TextStyle(color: Color(0xFF9AA6BD), fontSize: 12)),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Bildirishnomalar',
                    onPressed: _toggleSubscribe,
                    icon: Icon(
                      (_subscribed ?? d.subscribed) ? Icons.notifications_active : Icons.notifications_none,
                      color: (_subscribed ?? d.subscribed) ? const Color(0xFF34D399) : null,
                    ),
                  ),
                ]),
              ),
              if (d.ownerBio.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  child: Text(d.ownerBio, style: const TextStyle(color: Color(0xFF9AA6BD))),
                ),
              if (d.updates.isNotEmpty) _UpdatesFeed(updates: d.updates),
              const Divider(height: 1),
              if (d.products.isEmpty)
                const Padding(
                  padding: EdgeInsets.all(40),
                  child: Center(child: Text("Mahsulotlar yo'q")),
                )
              else
                ...d.products.map((p) => _ProductTile(
                    product: p,
                    cartEnabled: d.store.cartEnabled,
                    onAdd: () => _add(p))),
              const SizedBox(height: 24),
            ],
          );
        },
      ),
    );
  }
}

class _UpdatesFeed extends StatelessWidget {
  const _UpdatesFeed({required this.updates});
  final List<StoreUpdateItem> updates;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Yangiliklar',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: Color(0xFF9AA6BD))),
          const SizedBox(height: 6),
          ...updates.take(5).map((u) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Text('${u.updateTypeDisplay}${u.text.isNotEmpty ? ": ${u.text}" : ""}',
                    style: const TextStyle(fontSize: 13)),
              )),
        ],
      ),
    );
  }
}

class _ProductTile extends StatelessWidget {
  const _ProductTile({required this.product, required this.onAdd, this.cartEnabled = false});
  final Product product;
  final VoidCallback onAdd;
  final bool cartEnabled;

  @override
  Widget build(BuildContext context) {
    final out = product.stock <= 0;
    final countdown = out ? product.restockCountdownLabel() : null;
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
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(out ? "Omborda yo'q" : product.priceLabel,
              style: TextStyle(
                  color: out ? Colors.red.shade300 : const Color(0xFF34D399),
                  fontWeight: FontWeight.w700)),
          if (out && product.restockAt != null)
            Text(countdown ?? 'Tez orada kutilmoqda',
                style: const TextStyle(fontSize: 11, color: Color(0xFF9AA6BD))),
        ],
      ),
      trailing: cartEnabled
          ? FilledButton(
              onPressed: out ? null : onAdd,
              style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8)),
              child: const Icon(Icons.add, size: 20),
            )
          : null,
    );
  }
}
