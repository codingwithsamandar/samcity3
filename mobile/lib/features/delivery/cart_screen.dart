import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../payments/payment_sheet.dart';
import 'delivery_models.dart';

const int kDeliveryFee = 10000;

/// Savat ekrani: elementlar, miqdor boshqaruvi, checkout.
class CartScreen extends ConsumerStatefulWidget {
  const CartScreen({super.key});

  @override
  ConsumerState<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends ConsumerState<CartScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback(
        (_) => ref.read(cartControllerProvider.notifier).refresh());
  }

  @override
  Widget build(BuildContext context) {
    final cart = ref.watch(cartControllerProvider);
    // Pickup do'konlarida yetkazish narxi yo'q; olib ketish + yetkazish
    // aralashsa, yetkazish narxi faqat yetkazish do'konlari uchun qo'llanadi.
    final hasPickup = cart.items.any((it) => it.product.pickup);
    final hasDelivery = cart.items.any((it) => !it.product.pickup);
    final fee = hasDelivery ? kDeliveryFee : 0;
    final total = cart.items.isEmpty ? 0 : cart.subtotal + fee;

    return Scaffold(
      appBar: AppBar(title: const Text('Savat')),
      body: cart.items.isEmpty
          ? const Center(child: Text("Savatingiz bo'sh"))
          : Column(
              children: [
                Expanded(
                  child: ListView.separated(
                    padding: const EdgeInsets.all(12),
                    itemCount: cart.items.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) => _CartTile(item: cart.items[i]),
                  ),
                ),
                _Summary(
                  subtotal: cart.subtotal, fee: fee, total: total,
                  hasPickup: hasPickup, hasDelivery: hasDelivery,
                ),
              ],
            ),
    );
  }
}

class _CartTile extends ConsumerWidget {
  const _CartTile({required this.item});
  final CartItem item;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ctrl = ref.read(cartControllerProvider.notifier);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: SizedBox(
                width: 52, height: 52,
                child: item.product.cover != null
                    ? CachedNetworkImage(
                        imageUrl: item.product.cover!, fit: BoxFit.cover)
                    : Container(
                        color: const Color(0xFF141B29),
                        child: const Icon(Icons.fastfood, color: Color(0xFF69748A))),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(item.product.name,
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                  const SizedBox(height: 2),
                  Text("${money(item.lineTotal)} so'm",
                      style: const TextStyle(
                          color: Color(0xFF34D399), fontWeight: FontWeight.w700)),
                ],
              ),
            ),
            _QtyControl(
              quantity: item.quantity,
              onDec: () => ctrl.setQty(item.product.id, item.quantity - 1),
              onInc: () => ctrl.add(item.product.id),
              onRemove: () => ctrl.remove(item.product.id),
            ),
          ],
        ),
      ),
    );
  }
}

class _QtyControl extends StatelessWidget {
  const _QtyControl({
    required this.quantity,
    required this.onInc,
    required this.onDec,
    required this.onRemove,
  });
  final int quantity;
  final VoidCallback onInc, onDec, onRemove;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        IconButton(
          onPressed: quantity > 1 ? onDec : onRemove,
          icon: Icon(quantity > 1 ? Icons.remove : Icons.delete_outline, size: 20),
        ),
        Text('$quantity', style: const TextStyle(fontWeight: FontWeight.w700)),
        IconButton(onPressed: onInc, icon: const Icon(Icons.add, size: 20)),
      ],
    );
  }
}

class _Summary extends ConsumerWidget {
  const _Summary({
    required this.subtotal, required this.fee, required this.total,
    required this.hasPickup, required this.hasDelivery,
  });
  final int subtotal, fee, total;
  final bool hasPickup, hasDelivery;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      padding: EdgeInsets.fromLTRB(16, 12, 16, MediaQuery.of(context).padding.bottom + 12),
      decoration: const BoxDecoration(
        color: Color(0xFF0F1521),
        border: Border(top: BorderSide(color: Color(0x14FFFFFF))),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (hasPickup)
            const Padding(
              padding: EdgeInsets.only(bottom: 6),
              child: Text('🛍️ Olib ketish — oldindan karta orqali to\'lanadi',
                  style: TextStyle(fontSize: 12, color: Color(0xFF9AA6BD))),
            ),
          _row('Mahsulotlar', subtotal),
          if (hasDelivery) _row('Yetkazish', fee),
          const Divider(),
          _row('Jami', total, bold: true),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: () => _openCheckout(context, ref, total),
              child: const Text('Buyurtmani rasmiylashtirish'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _row(String label, int value, {bool bold = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label,
                style: TextStyle(
                    color: bold ? Colors.white : const Color(0xFF9AA6BD),
                    fontWeight: bold ? FontWeight.w800 : FontWeight.normal,
                    fontSize: bold ? 17 : 14)),
            Text("${money(value)} so'm",
                style: TextStyle(
                    fontWeight: bold ? FontWeight.w800 : FontWeight.w600,
                    fontSize: bold ? 17 : 14)),
          ],
        ),
      );

  Future<void> _openCheckout(BuildContext context, WidgetRef ref, int total) async {
    final outcome = await showModalBottomSheet<_CheckoutOutcome>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1521),
      builder: (_) => _CheckoutSheet(total: total, hasPickup: hasPickup, hasDelivery: hasDelivery),
    );
    if (outcome == null) return;
    ref.read(cartControllerProvider.notifier).clearLocal();

    if (outcome.online) {
      // Har bir buyurtma uchun (multi-store split) to'lovni ketma-ket ochamiz.
      for (var i = 0; i < outcome.orders.length; i++) {
        if (!context.mounted) return;
        final o = outcome.orders[i];
        await showPaymentSheet(
          context, ref,
          targetType: 'order',
          targetId: o.id,
          title: outcome.orders.length > 1
              ? "To'lov ${i + 1}/${outcome.orders.length}"
              : "Buyurtma to'lovi",
        );
      }
    } else if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: const Text('Buyurtma qabul qilindi! ✅'),
        backgroundColor: Colors.green.shade700,
      ));
    }
  }
}

/// Checkout varaqasi natijasi.
class _CheckoutOutcome {
  final List<DeliveryOrder> orders;
  final bool online;
  _CheckoutOutcome({required this.orders, required this.online});
}

class _CheckoutSheet extends ConsumerStatefulWidget {
  const _CheckoutSheet({required this.total, required this.hasPickup, required this.hasDelivery});
  final int total;
  final bool hasPickup, hasDelivery;

  @override
  ConsumerState<_CheckoutSheet> createState() => _CheckoutSheetState();
}

class _CheckoutSheetState extends ConsumerState<_CheckoutSheet> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _address = TextEditingController();
  String _method = 'cash'; // cash | online
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    // Pickup buyurtmasi faqat karta (onlayn) orqali oldindan to'lanadi.
    if (widget.hasPickup) _method = 'online';
  }

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _address.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_phone.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Telefon majburiy')));
      return;
    }
    if (widget.hasDelivery && _address.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Yetkazib berish uchun manzil majburiy')));
      return;
    }
    // Pickup uchun to'lov MAJBURIY oldindan — karta.
    final method = (widget.hasPickup || _method == 'online') ? 'card' : 'cash';
    setState(() => _loading = true);
    try {
      final result = await ref.read(deliveryRepositoryProvider).checkout(
            fullName: _name.text.trim(),
            phone: _phone.text.trim(),
            address: widget.hasDelivery ? _address.text.trim() : '',
            paymentMethod: method,
          );
      if (mounted) {
        // Karta bo'lsa — to'lov varaqasiga o'tamiz (Payme/Click).
        Navigator.pop(
          context,
          _CheckoutOutcome(orders: result.orders, online: method == 'card'),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Buyurtma yuborilmadi')));
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16, right: 16, top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(widget.hasPickup ? 'Olib ketish buyurtmasi' : 'Buyurtmani rasmiylashtirish',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 14),
          TextField(controller: _name,
              decoration: const InputDecoration(labelText: 'Ism (ixtiyoriy)')),
          const SizedBox(height: 10),
          TextField(controller: _phone,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Telefon *')),
          if (widget.hasDelivery) ...[
            const SizedBox(height: 10),
            TextField(controller: _address,
                decoration: const InputDecoration(labelText: 'Manzil *')),
          ],
          const SizedBox(height: 14),
          if (!widget.hasPickup)
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'cash', label: Text('Naqd'), icon: Icon(Icons.payments)),
                ButtonSegment(value: 'online', label: Text('Onlayn'), icon: Icon(Icons.credit_card)),
              ],
              selected: {_method},
              onSelectionChanged: (s) => setState(() => _method = s.first),
            ),
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              widget.hasPickup
                  ? "🛍️ Do'kondan o'zingiz olib ketasiz. To'lov oldindan Payme/Click orqali."
                  : (_method == 'online'
                      ? "💳 Payme yoki Click orqali xavfsiz to'lov."
                      : "🚚 To'lov yetkazib berishda naqd pulda."),
              style: const TextStyle(fontSize: 11, color: Color(0xFF69748A)),
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _loading ? null : _submit,
            child: _loading
                ? const SizedBox(
                    height: 20, width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : Text((widget.hasPickup || _method == 'online')
                    ? "${money(widget.total)} so'm — to'lovga o'tish"
                    : "${money(widget.total)} so'm — tasdiqlash"),
          ),
        ],
      ),
    );
  }
}
