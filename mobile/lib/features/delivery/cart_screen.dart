import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../core/providers.dart';
import '../payments/payment_sheet.dart';
import 'delivery_models.dart';
import 'location_picker.dart';

const int kDeliveryFee = 10000;

/// Savat ekrani: 3 bo'lim (e'lonlar / yetkazish / mahalla) + saqlangan savatlar,
/// hammasiga birdan bitta to'lov.
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

  Future<void> _newCart() async {
    final name = await _askName('Yangi savat', '');
    if (name == null) return;
    await ref.read(cartControllerProvider.notifier).createCart(name);
  }

  Future<void> _renameCart(Cart cart) async {
    final name = await _askName('Savat nomi', cart.name);
    if (name == null || name.isEmpty) return;
    await ref.read(cartControllerProvider.notifier).renameCart(cart.id, name);
  }

  Future<void> _deleteCart(Cart cart) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text("Savatni o'chirish"),
        content: Text("«${cart.name}» savati o'chirilsinmi?"),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Yo\'q')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('O\'chirish')),
        ],
      ),
    );
    if (ok == true) await ref.read(cartControllerProvider.notifier).deleteCart(cart.id);
  }

  Future<String?> _askName(String title, String initial) async {
    final ctrl = TextEditingController(text: initial);
    return showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(title),
        content: TextField(controller: ctrl, autofocus: true,
            decoration: const InputDecoration(hintText: 'Savat nomi')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Bekor')),
          FilledButton(onPressed: () => Navigator.pop(context, ctrl.text.trim()), child: const Text('Saqlash')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cart = ref.watch(cartControllerProvider);
    final ctrl = ref.read(cartControllerProvider.notifier);
    final hasPickup = cart.mahallaItems.isNotEmpty;
    final hasDelivery = cart.deliveryItems.isNotEmpty;
    final fee = hasDelivery ? kDeliveryFee : 0;
    final total = cart.hasProducts ? cart.subtotal + fee : 0;

    return Scaffold(
      appBar: AppBar(
        title: Text('Savat — ${cart.name}'),
        actions: [
          PopupMenuButton<String>(
            onSelected: (v) {
              if (v == 'new') _newCart();
              if (v == 'rename') _renameCart(cart);
              if (v == 'delete') _deleteCart(cart);
            },
            itemBuilder: (_) => [
              const PopupMenuItem(value: 'new', child: Text('➕ Yangi savat')),
              const PopupMenuItem(value: 'rename', child: Text("✏️ Nomini o'zgartirish")),
              if (cart.carts.length > 1)
                const PopupMenuItem(value: 'delete', child: Text("🗑 Savatni o'chirish")),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          if (cart.carts.length > 1) _CartSwitcher(carts: cart.carts, onSelect: ctrl.activateCart),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(12),
              children: [
                _Section(
                  title: "📢 Saqlangan e'lonlar",
                  subtitle: 'keyin ko\'rish uchun',
                  empty: cart.ads.isEmpty,
                  emptyText: "Saqlangan e'lon yo'q",
                  children: cart.ads.map((a) => _AdTile(ad: a, onRemove: () => ctrl.removeAd(a.id))).toList(),
                ),
                _Section(
                  title: '🚚 Yetkazib berish do\'konlari',
                  subtitle: "${money(cart.deliverySubtotal)} so'm",
                  empty: cart.deliveryItems.isEmpty,
                  emptyText: 'Mahsulot yo\'q',
                  children: cart.deliveryItems.map((it) => _CartTile(item: it)).toList(),
                ),
                _Section(
                  title: '🛒 Mahalla do\'konlari',
                  subtitle: "${money(cart.mahallaSubtotal)} so'm · olib ketish",
                  empty: cart.mahallaItems.isEmpty,
                  emptyText: 'Mahsulot yo\'q',
                  children: cart.mahallaItems.map((it) => _CartTile(item: it)).toList(),
                ),
              ],
            ),
          ),
          if (cart.hasProducts)
            _Summary(
              subtotal: cart.subtotal, fee: fee, total: total,
              hasPickup: hasPickup, hasDelivery: hasDelivery,
            ),
        ],
      ),
    );
  }
}

class _CartSwitcher extends StatelessWidget {
  const _CartSwitcher({required this.carts, required this.onSelect});
  final List<SavedCart> carts;
  final Future<void> Function(String) onSelect;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 48,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        children: carts.map((c) {
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ChoiceChip(
              label: Text('${c.name} (${c.itemCount})'),
              selected: c.isActive,
              onSelected: (_) { if (!c.isActive) onSelect(c.id); },
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({
    required this.title, required this.subtitle,
    required this.empty, required this.emptyText, required this.children,
  });
  final String title, subtitle, emptyText;
  final bool empty;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 12, 4, 6),
          child: Row(children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            const SizedBox(width: 8),
            Text(subtitle, style: const TextStyle(fontSize: 12, color: Color(0xFF69748A))),
          ]),
        ),
        if (empty)
          Padding(
            padding: const EdgeInsets.fromLTRB(4, 0, 4, 4),
            child: Text(emptyText, style: const TextStyle(color: Color(0xFF69748A), fontSize: 13)),
          )
        else
          ...children,
      ],
    );
  }
}

class _AdTile extends StatelessWidget {
  const _AdTile({required this.ad, required this.onRemove});
  final CartAdItem ad;
  final VoidCallback onRemove;
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(8),
        child: Row(children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: SizedBox(
              width: 52, height: 52,
              child: ad.cover != null
                  ? CachedNetworkImage(imageUrl: ad.cover!, fit: BoxFit.cover)
                  : Container(
                      color: const Color(0xFF141B29),
                      child: const Icon(Icons.sell_outlined, color: Color(0xFF69748A))),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(ad.title, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 2),
                Text(ad.priceLabel, style: const TextStyle(color: Color(0xFF9AA6BD), fontSize: 12)),
              ],
            ),
          ),
          IconButton(onPressed: onRemove, icon: const Icon(Icons.delete_outline, size: 20)),
        ]),
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
                    ? CachedNetworkImage(imageUrl: item.product.cover!, fit: BoxFit.cover)
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
                  Text(item.product.name, maxLines: 1, overflow: TextOverflow.ellipsis),
                  const SizedBox(height: 2),
                  Text("${money(item.lineTotal)} so'm",
                      style: const TextStyle(color: Color(0xFF34D399), fontWeight: FontWeight.w700)),
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
              child: const Text('Hammasiga birdan to\'lash'),
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

    // Bitta birlashgan to'lov — barcha buyurtmalar bitta checkout guruhida.
    if (outcome.online && outcome.checkoutId.isNotEmpty) {
      if (!context.mounted) return;
      await showPaymentSheet(
        context, ref,
        targetType: 'checkout',
        targetId: outcome.checkoutId,
        title: "Buyurtma to'lovi",
      );
    } else if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: const Text('Buyurtma qabul qilindi! ✅'),
        backgroundColor: Colors.green.shade700,
      ));
    }
    if (context.mounted) ref.read(cartControllerProvider.notifier).refresh();
  }
}

/// Checkout varaqasi natijasi.
class _CheckoutOutcome {
  final String checkoutId;
  final bool online;
  _CheckoutOutcome({required this.checkoutId, required this.online});
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
  LatLng? _location; // xaritada/GPS bilan belgilangan joylashuv

  @override
  void initState() {
    super.initState();
    if (widget.hasPickup) _method = 'online';
  }

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _address.dispose();
    super.dispose();
  }

  Future<void> _pickLocation() async {
    FocusScope.of(context).unfocus();
    final picked = await Navigator.of(context).push<LatLng>(
      MaterialPageRoute(builder: (_) => LocationPickerScreen(initial: _location)),
    );
    if (picked == null || !mounted) return;
    setState(() {
      _location = picked;
      // Manzil bo'sh bo'lsa — koordinatani mo'ljal sifatida yozib qo'yamiz.
      if (_address.text.trim().isEmpty) {
        _address.text =
            '📍 ${picked.latitude.toStringAsFixed(5)}, ${picked.longitude.toStringAsFixed(5)}';
      }
    });
  }

  Future<void> _submit() async {
    if (_phone.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Telefon majburiy')));
      return;
    }
    if (widget.hasDelivery && _address.text.trim().isEmpty && _location == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Yetkazib berish uchun manzil yoki xaritada joy belgilang')));
      return;
    }
    final method = (widget.hasPickup || _method == 'online') ? 'card' : 'cash';
    setState(() => _loading = true);
    try {
      final result = await ref.read(deliveryRepositoryProvider).checkout(
            fullName: _name.text.trim(),
            phone: _phone.text.trim(),
            address: widget.hasDelivery ? _address.text.trim() : '',
            latitude: widget.hasDelivery ? _location?.latitude : null,
            longitude: widget.hasDelivery ? _location?.longitude : null,
            paymentMethod: method,
          );
      if (mounted) {
        Navigator.pop(
          context,
          _CheckoutOutcome(checkoutId: result.checkoutId, online: method == 'card'),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Buyurtma yuborilmadi')));
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.of(context);
    return SingleChildScrollView(
      padding: EdgeInsets.only(
        left: 16, right: 16, top: 16,
        // Klaviatura (viewInsets) + tizim navigatsiya paneli (padding.bottom) —
        // tasdiqlash tugmasi hech qachon panel ostida kesilib qolmasin.
        bottom: media.viewInsets.bottom + media.padding.bottom + 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(widget.hasPickup ? 'Olib ketish buyurtmasi' : 'Buyurtmani rasmiylashtirish',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 14),
          TextField(controller: _name, decoration: const InputDecoration(labelText: 'Ism (ixtiyoriy)')),
          const SizedBox(height: 10),
          TextField(controller: _phone, keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Telefon *')),
          if (widget.hasDelivery) ...[
            const SizedBox(height: 10),
            TextField(
              controller: _address,
              decoration: const InputDecoration(
                labelText: 'Manzil *',
                hintText: "Ko'cha, uy, mo'ljal",
              ),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _loading ? null : _pickLocation,
              icon: Icon(_location == null ? Icons.map_outlined : Icons.check_circle,
                  color: _location == null ? null : const Color(0xFF34D399)),
              label: Text(_location == null
                  ? 'Joriy joylashuv yoki xaritadan belgilash'
                  : 'Joylashuv belgilandi — o\'zgartirish'),
            ),
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
                      ? "💳 Payme yoki Click orqali xavfsiz to'lov (hammasiga birdan)."
                      : "🚚 To'lov yetkazib berishda naqd pulda."),
              style: const TextStyle(fontSize: 11, color: Color(0xFF69748A)),
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _loading ? null : _submit,
            child: _loading
                ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : Text((widget.hasPickup || _method == 'online')
                    ? "${money(widget.total)} so'm — to'lovga o'tish"
                    : "${money(widget.total)} so'm — tasdiqlash"),
          ),
        ],
      ),
    );
  }
}
