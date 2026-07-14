import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/dialer.dart';
import '../../core/providers.dart';
import 'courier_models.dart';
import 'delivery_models.dart';

const _muted = Color(0xFF9AA0AC);
const _statBg = Color(0xFF141B29);
const _green = Color(0xFF34D399);
const _gold = Color(0xFFCAA23A);

/// Kuryer paneli — buyurtma qabul qilish, yetkazish, daromad.
class CourierDashboardScreen extends ConsumerStatefulWidget {
  const CourierDashboardScreen({super.key});

  @override
  ConsumerState<CourierDashboardScreen> createState() => _CourierDashboardScreenState();
}

class _CourierDashboardScreenState extends ConsumerState<CourierDashboardScreen> {
  bool _loading = true;
  String? _error;
  bool _busy = false;
  CourierDashboard? _data;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await ref.read(courierRepositoryProvider).dashboard();
      if (mounted) setState(() { _data = d; _loading = false; _error = null; });
    } catch (_) {
      if (mounted) setState(() { _loading = false; _error = 'Yuklab bo\'lmadi'; });
    }
  }

  void _toast(String msg, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg),
      backgroundColor: error ? Colors.red.shade700 : _green.withValues(alpha: 0.9),
    ));
  }

  Future<void> _guard(Future<void> Function() action) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await action();
    } catch (e) {
      _toast('Xatolik yuz berdi', error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _toggleAvailable() => _guard(() async {
        final on = await ref.read(courierRepositoryProvider).toggleAvailable();
        _toast(on ? "Holat: Bo'sh ✅" : 'Holat: Band ⛔');
        await _load();
      });

  Future<void> _accept(DeliveryOrder o) => _guard(() async {
        await ref.read(courierRepositoryProvider).accept(o.id);
        _toast('Buyurtma qabul qilindi! 🚗');
        await _load();
      });

  Future<void> _release(DeliveryOrder o) => _guard(() async {
        await ref.read(courierRepositoryProvider).release(o.id);
        _toast('Buyurtmadan voz kechildi.');
        await _load();
      });

  Future<void> _status(DeliveryOrder o, String status, String label) => _guard(() async {
        await ref.read(courierRepositoryProvider).setStatus(o.id, status);
        _toast(label);
        await _load();
      });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('🚲 Kuryer paneli')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : _data!.registered
                  ? _buildDashboard(_data!)
                  : _CourierRegisterForm(onDone: _load),
    );
  }

  Widget _buildDashboard(CourierDashboard d) {
    final p = d.profile!;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          // ── Profil + bo'sh/band ──
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(p.fullName, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text('${p.vehicleDisplay} · ${p.vehicleNumber}', style: const TextStyle(color: _muted)),
                const SizedBox(height: 10),
                Row(children: [
                  Icon(Icons.circle, size: 12, color: p.isAvailable ? _green : Colors.grey),
                  const SizedBox(width: 6),
                  Text(p.isAvailable ? "Bo'sh" : 'Band',
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                  const Spacer(),
                  Switch(
                    value: p.isAvailable,
                    onChanged: _busy ? null : (_) => _toggleAvailable(),
                  ),
                ]),
              ]),
            ),
          ),
          const SizedBox(height: 6),
          // ── Statistika ──
          _statsRow(d.stats),
          const SizedBox(height: 14),
          // ── Faol buyurtmalar ──
          _sectionTitle('Faol buyurtmalar', d.active.length),
          if (d.active.isEmpty)
            _empty('Faol buyurtma yo\'q.')
          else
            ...d.active.map((o) => _activeCard(o)),
          const SizedBox(height: 14),
          // ── Qabul qilish mumkin ──
          _sectionTitle('Qabul qilish mumkin', d.available.length),
          if (d.available.isEmpty)
            _empty('Hozircha tayyor buyurtma yo\'q.')
          else
            ...d.available.map((o) => _availableCard(o)),
          const SizedBox(height: 14),
          // ── Tarix ──
          if (d.history.isNotEmpty) ...[
            _sectionTitle('Yetkazilgan', d.stats.deliveredCount),
            ...d.history.take(10).map((o) => _historyTile(o)),
          ],
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _statsRow(CourierStats s) => Row(children: [
        _stat('${s.deliveredCount}', 'Yetkazilgan'),
        const SizedBox(width: 8),
        _stat('${s.activeCount}', 'Faol'),
        const SizedBox(width: 8),
        _stat(_money(s.earningsToday), 'Bugun'),
        const SizedBox(width: 8),
        _stat(_money(s.earningsTotal), 'Jami'),
      ]);

  Widget _stat(String value, String label) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
          decoration: BoxDecoration(color: _statBg, borderRadius: BorderRadius.circular(10)),
          child: Column(children: [
            Text(value, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
                maxLines: 1, overflow: TextOverflow.ellipsis),
            const SizedBox(height: 2),
            Text(label, style: const TextStyle(fontSize: 10, color: _muted),
                textAlign: TextAlign.center),
          ]),
        ),
      );

  Widget _sectionTitle(String t, int n) => Padding(
        padding: const EdgeInsets.only(bottom: 8, top: 4),
        child: Text('$t ($n)', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
      );

  Widget _empty(String t) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: Text(t, style: const TextStyle(color: _muted)),
      );

  Widget _orderInfo(DeliveryOrder o) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('#${o.id.substring(0, 8)} · ${_money(o.total)} so\'m',
              style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 2),
          if (o.address.isNotEmpty)
            Text('📍 ${o.address}', style: const TextStyle(color: _muted, fontSize: 13)),
          if (o.phone.isNotEmpty)
            Align(alignment: Alignment.centerLeft, child: PhoneLink(o.phone)),
          if (o.items.isNotEmpty)
            Text(o.items.map((i) => '${i.productName}×${i.quantity}').join(', '),
                style: const TextStyle(fontSize: 12), maxLines: 2, overflow: TextOverflow.ellipsis),
          Text('Yetkazish haqi: ${_money(o.deliveryFee)} so\'m',
              style: const TextStyle(fontSize: 12, color: _gold)),
        ],
      );

  Widget _activeCard(DeliveryOrder o) {
    // Keyingi holat tugmasi statusga qarab.
    final next = o.status == 'assigned'
        ? ('on_the_way', 'Yo\'lga chiqdim', "Yo'lda ✅")
        : ('delivered', 'Yetkazdim', 'Yetkazildi ✅');
    return Card(
      color: const Color(0xFF16202E),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(o.label, style: const TextStyle(fontWeight: FontWeight.w700))),
            Text(o.fullName, style: const TextStyle(color: _muted, fontSize: 12)),
          ]),
          const SizedBox(height: 6),
          _orderInfo(o),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(
              child: FilledButton(
                onPressed: _busy ? null : () => _status(o, next.$1, next.$3),
                child: Text(next.$2),
              ),
            ),
            const SizedBox(width: 8),
            if (o.status == 'assigned')
              OutlinedButton(
                onPressed: _busy ? null : () => _release(o),
                child: const Text('Voz kechish'),
              ),
          ]),
        ]),
      ),
    );
  }

  Widget _availableCard(DeliveryOrder o) => Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _orderInfo(o),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _busy ? null : () => _accept(o),
                icon: const Icon(Icons.check),
                label: const Text('Qabul qilish'),
              ),
            ),
          ]),
        ),
      );

  Widget _historyTile(DeliveryOrder o) => ListTile(
        dense: true,
        leading: const Icon(Icons.check_circle, color: _green, size: 20),
        title: Text('#${o.id.substring(0, 8)} · ${o.address}',
            maxLines: 1, overflow: TextOverflow.ellipsis),
        trailing: Text('${_money(o.deliveryFee)} so\'m',
            style: const TextStyle(color: _gold, fontSize: 13)),
      );

  static String _money(int v) {
    final s = v.toString();
    final b = StringBuffer();
    for (int i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) b.write(' ');
      b.write(s[i]);
    }
    return b.toString();
  }
}

/// Kuryer ro'yxatdan o'tish formasi.
class _CourierRegisterForm extends ConsumerStatefulWidget {
  const _CourierRegisterForm({required this.onDone});
  final Future<void> Function() onDone;

  @override
  ConsumerState<_CourierRegisterForm> createState() => _CourierRegisterFormState();
}

class _CourierRegisterFormState extends ConsumerState<_CourierRegisterForm> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _number = TextEditingController();
  String _vehicle = 'moto';
  bool _busy = false;

  static const _vehicles = [
    ('foot', '🚶 Piyoda'),
    ('bike', '🚲 Velosiped'),
    ('moto', '🏍️ Mototsikl'),
    ('car', '🚗 Avtomobil'),
  ];

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _number.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_name.text.trim().isEmpty || _phone.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Ism va telefon majburiy.')));
      return;
    }
    setState(() => _busy = true);
    try {
      await ref.read(courierRepositoryProvider).register(
            fullName: _name.text.trim(),
            phone: _phone.text.trim(),
            vehicleType: _vehicle,
            vehicleNumber: _number.text.trim(),
          );
      await widget.onDone();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Ro\'yxatdan o\'tishda xatolik.')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('Kuryer bo\'lish',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        const Text('Yetkazib beruvchi sifatida ro\'yxatdan o\'ting va buyurtmalarni qabul qiling.',
            style: TextStyle(color: _muted)),
        const SizedBox(height: 20),
        TextField(controller: _name, decoration: const InputDecoration(labelText: 'Ism familiya *')),
        const SizedBox(height: 12),
        TextField(
          controller: _phone,
          keyboardType: TextInputType.phone,
          decoration: const InputDecoration(labelText: 'Telefon *', hintText: '+998 90 123 45 67'),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _vehicle,
          decoration: const InputDecoration(labelText: 'Transport turi'),
          items: _vehicles
              .map((v) => DropdownMenuItem(value: v.$1, child: Text(v.$2)))
              .toList(),
          onChanged: (v) => setState(() => _vehicle = v ?? 'moto'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _number,
          decoration: const InputDecoration(labelText: 'Davlat raqami (ixtiyoriy)'),
        ),
        const SizedBox(height: 20),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: _busy ? null : _submit,
            child: Text(_busy ? 'Yuborilmoqda...' : 'Ro\'yxatdan o\'tish'),
          ),
        ),
      ],
    );
  }
}
