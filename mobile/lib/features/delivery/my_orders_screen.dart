import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_error.dart';
import '../../core/providers.dart';
import '../../core/track_socket.dart';
import '../payments/payment_sheet.dart';
import 'delivery_models.dart';

/// Foydalanuvchining yetkazish buyurtmalari — holat kuzatuvi + to'lov.
/// Faol buyurtmalar uchun WebSocket orqali holat JONLI yangilanadi
/// (sahifani yangilamasdan).
class MyOrdersScreen extends ConsumerStatefulWidget {
  const MyOrdersScreen({super.key});

  @override
  ConsumerState<MyOrdersScreen> createState() => _MyOrdersScreenState();
}

class _MyOrdersScreenState extends ConsumerState<MyOrdersScreen> {
  // Buyurtma holatlari tartibi (cancelled alohida).
  static const _flow = [
    'pending', 'accepted', 'preparing', 'ready',
    'assigned', 'picked_up', 'on_the_way', 'delivered',
  ];
  static const _finished = {'delivered', 'cancelled'};

  List<DeliveryOrder>? _orders;
  bool _loading = true;
  Object? _error;

  // WS orqali kelgan jonli holat (order.id -> status / displayed text).
  final Map<String, String> _liveStatus = {};
  final Map<String, String> _liveDisplay = {};
  final List<TrackSocket> _sockets = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _closeSockets();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final list = await ref.read(deliveryRepositoryProvider).orders();
      if (!mounted) return;
      setState(() {
        _orders = list;
        _loading = false;
        _error = null;
      });
      _openSockets(list);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _loading = false;
      });
    }
  }

  void _closeSockets() {
    for (final s in _sockets) {
      s.dispose();
    }
    _sockets.clear();
  }

  /// Faol (yakunlanmagan) buyurtmalarga jonli kuzatuv ulanadi.
  void _openSockets(List<DeliveryOrder> orders) {
    _closeSockets();
    final storage = ref.read(tokenStorageProvider);
    for (final o in orders) {
      final live = _liveStatus[o.id] ?? o.status;
      if (_finished.contains(live)) continue;
      final sock = TrackSocket(storage, 'delivery/track/${o.id}');
      sock.events.listen((data) => _onStatus(o.id, data));
      sock.connect();
      _sockets.add(sock);
    }
  }

  void _onStatus(String orderId, Map<String, dynamic> data) {
    final type = data['type'];
    if (type != 'status' && type != 'snapshot') return;
    final status = data['status'] as String?;
    final display = data['status_display'] as String?;
    if (status == null) return;
    if (!mounted) return;
    setState(() {
      _liveStatus[orderId] = status;
      if (display != null) _liveDisplay[orderId] = display;
    });
  }

  Future<void> _pay(DeliveryOrder o) async {
    await showPaymentSheet(context, ref,
        targetType: 'order', targetId: o.id, title: "Buyurtma to'lovi");
    _load();
  }

  Future<void> _confirmPickup(DeliveryOrder o) async {
    try {
      await ref.read(deliveryRepositoryProvider).confirmPickup(o.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Qabul qilinganingiz tasdiqlandi. Rahmat!')));
      }
      _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(apiErrorMessage(e))));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Buyurtmalarim')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return ListView(children: [
        const SizedBox(height: 120),
        Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(apiErrorMessage(_error!), textAlign: TextAlign.center),
          ),
        ),
      ]);
    }
    final orders = _orders ?? [];
    if (orders.isEmpty) {
      return ListView(children: const [
        SizedBox(height: 120),
        Center(
          child: Column(children: [
            Icon(Icons.receipt_long_outlined, size: 48, color: Color(0xFF69748A)),
            SizedBox(height: 8),
            Text("Hali buyurtmalar yo'q"),
          ]),
        ),
      ]);
    }
    return ListView.separated(
      padding: const EdgeInsets.all(12),
      itemCount: orders.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, i) {
        final o = orders[i];
        return _OrderCard(
          order: o,
          flow: _flow,
          statusOverride: _liveStatus[o.id],
          displayOverride: _liveDisplay[o.id],
          onPay: () => _pay(o),
          onConfirmPickup: () => _confirmPickup(o),
        );
      },
    );
  }
}

class _OrderCard extends StatelessWidget {
  const _OrderCard({
    required this.order,
    required this.flow,
    required this.onPay,
    required this.onConfirmPickup,
    this.statusOverride,
    this.displayOverride,
  });
  final DeliveryOrder order;
  final List<String> flow;
  final VoidCallback onPay;
  final VoidCallback onConfirmPickup;
  final String? statusOverride;
  final String? displayOverride;

  @override
  Widget build(BuildContext context) {
    final status = statusOverride ?? order.status;
    final statusText = displayOverride ?? order.label;
    // Pickup: mahsulot tayyor bo'lganda mijoz "qabul qildim" deb tasdiqlaydi.
    final canConfirm = order.canConfirmPickup && status == 'ready';
    final cancelled = status == 'cancelled';
    final stepIndex = flow.indexOf(status);
    final progress = cancelled
        ? 0.0
        : (stepIndex < 0 ? 0.0 : (stepIndex + 1) / flow.length);
    final canPay = !order.isPaid && !cancelled;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('Buyurtma #${order.id.substring(0, 8)}',
                      style: const TextStyle(fontWeight: FontWeight.w800)),
                ),
                _StatusChip(
                    label: cancelled ? 'Bekor qilingan' : statusText,
                    color: cancelled
                        ? Colors.red.shade300
                        : (status == 'delivered'
                            ? const Color(0xFF34D399)
                            : const Color(0xFF22D3EE))),
              ],
            ),
            const SizedBox(height: 10),
            if (!cancelled)
              ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: LinearProgressIndicator(
                  value: progress,
                  minHeight: 6,
                  backgroundColor: const Color(0xFF1B2535),
                  color: const Color(0xFF34D399),
                ),
              ),
            const SizedBox(height: 10),
            // Mahsulotlar
            ...order.items.take(4).map((it) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text('${it.productName} × ${it.quantity}',
                            maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                fontSize: 13, color: Color(0xFF9AA6BD))),
                      ),
                      Text("${money(it.lineTotal)} so'm",
                          style: const TextStyle(fontSize: 13)),
                    ],
                  ),
                )),
            const Divider(height: 18),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(children: [
                  Icon(
                    order.isPaid ? Icons.check_circle : Icons.schedule,
                    size: 16,
                    color: order.isPaid
                        ? const Color(0xFF34D399)
                        : const Color(0xFFCAA23A),
                  ),
                  const SizedBox(width: 4),
                  Text(order.isPaid ? "To'langan" : "To'lanmagan",
                      style: const TextStyle(fontSize: 12)),
                ]),
                Text("${money(order.total)} so'm",
                    style: const TextStyle(
                        fontWeight: FontWeight.w800, fontSize: 16)),
              ],
            ),
            if (canPay) ...[
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: onPay,
                  icon: const Icon(Icons.credit_card, size: 18),
                  label: const Text("Onlayn to'lash"),
                ),
              ),
            ],
            if (canConfirm) ...[
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
                  onPressed: onConfirmPickup,
                  icon: const Icon(Icons.check_circle_outline, size: 18),
                  label: const Text("Qabul qildim"),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(label,
          style: TextStyle(
              color: color, fontSize: 12, fontWeight: FontWeight.w700)),
    );
  }
}
