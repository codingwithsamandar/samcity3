import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../delivery/delivery_models.dart' show money;
import 'taxi_models.dart' show TaxiRoute;
import 'taxist_panel_models.dart';

const _muted = Color(0xFF9AA0AC);
const _statBg = Color(0xFF141B29);
const _green = Color(0xFF34D399);
const _gold = Color(0xFFCAA23A);

/// Haydovchi (taksist) paneli — profil, onlayn holati, marshrutlar, sayohatlar.
class TaxistPanelScreen extends ConsumerStatefulWidget {
  const TaxistPanelScreen({super.key});

  @override
  ConsumerState<TaxistPanelScreen> createState() => _TaxistPanelScreenState();
}

class _TaxistPanelScreenState extends ConsumerState<TaxistPanelScreen> {
  bool _loading = true;
  String? _error;
  bool _busy = false;
  TaxistPanel? _data;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await ref.read(taxistPanelRepositoryProvider).panel();
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

  Future<void> _toggleOnline() => _guard(() async {
        final on = await ref.read(taxistPanelRepositoryProvider).toggleOnline();
        _toast(on ? 'Holat: Onlayn ✅' : 'Holat: Oflayn ⛔');
        await _load();
      });

  Future<void> _deleteRoute(TaxiRoute r) => _guard(() async {
        await ref.read(taxistPanelRepositoryProvider).deleteRoute(r.id);
        _toast('Marshrut o\'chirildi.');
        await _load();
      });

  Future<void> _addRoute() async {
    final added = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const _AddRouteSheet(),
    );
    if (added == true) await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('🚕 Haydovchi paneli')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : _data!.registered
                  ? _buildPanel(_data!)
                  : _TaxistRegisterForm(onDone: _load),
    );
  }

  Widget _buildPanel(TaxistPanel d) {
    final p = d.profile!;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          // ── Profil + onlayn holati ──
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                    child: Text(p.fullName,
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                  ),
                  if (p.avgRating > 0)
                    Text('⭐ ${p.avgRating.toStringAsFixed(1)}',
                        style: const TextStyle(color: _gold, fontWeight: FontWeight.w700)),
                ]),
                const SizedBox(height: 4),
                Text(
                  [
                    if (p.carModel.isNotEmpty) p.carModel,
                    if (p.region.isNotEmpty) p.region,
                    p.phone,
                  ].join(' · '),
                  style: const TextStyle(color: _muted),
                ),
                const SizedBox(height: 10),
                Row(children: [
                  Icon(Icons.circle, size: 12, color: p.isOnline ? _green : Colors.grey),
                  const SizedBox(width: 6),
                  Text(p.isOnline ? 'Onlayn' : 'Oflayn',
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                  const Spacer(),
                  Switch(
                    value: p.isOnline,
                    onChanged: _busy ? null : (_) => _toggleOnline(),
                  ),
                ]),
              ]),
            ),
          ),
          const SizedBox(height: 6),
          // ── Statistika ──
          _statsRow(d.stats),
          const SizedBox(height: 14),
          // ── Marshrutlar ──
          Row(children: [
            Expanded(child: _sectionTitle('AB marshrutlarim', d.routes.length)),
            TextButton.icon(
              onPressed: _busy ? null : _addRoute,
              icon: const Icon(Icons.add, size: 18),
              label: const Text('Qo\'shish'),
            ),
          ]),
          if (d.routes.isEmpty)
            _empty('Hali marshrut yo\'q. «Qo\'shish» orqali A→B narxini belgilang.')
          else
            ...d.routes.map(_routeCard),
          const SizedBox(height: 14),
          // ── Faol sayohatlar ──
          _sectionTitle('Faol sayohatlar', d.active.length),
          if (d.active.isEmpty)
            _empty('Faol buyurtma yo\'q.')
          else
            ...d.active.map((t) => _tripCard(t, active: true)),
          const SizedBox(height: 14),
          // ── Tarix ──
          if (d.history.isNotEmpty) ...[
            _sectionTitle('Yakunlangan', d.stats.completedCount),
            ...d.history.map((t) => _tripCard(t, active: false)),
          ],
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _statsRow(TaxistStats s) => Row(children: [
        _stat('${s.completedCount}', 'Yakunlangan'),
        const SizedBox(width: 8),
        _stat('${s.activeCount}', 'Faol'),
        const SizedBox(width: 8),
        _stat('${s.routesCount}', 'Marshrut'),
        const SizedBox(width: 8),
        _stat(money(s.earningsTotal), 'Daromad'),
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

  Widget _routeCard(TaxiRoute r) => Card(
        child: ListTile(
          title: Text('${r.pointA} → ${r.pointB}',
              style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text(
            [
              "Yo'lovchi: ${money(r.passengerPrice)} so'm",
              if (r.deliveryPrice != null) "Dostavka: ${money(r.deliveryPrice!)} so'm",
              if (r.note.isNotEmpty) r.note,
            ].join(' · '),
            style: const TextStyle(fontSize: 12),
          ),
          trailing: IconButton(
            icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
            onPressed: _busy ? null : () => _deleteRoute(r),
          ),
        ),
      );

  Widget _tripCard(DriverTrip t, {required bool active}) => Card(
        color: active ? const Color(0xFF16202E) : null,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(
                child: Text('${t.pointA} → ${t.pointB}',
                    style: const TextStyle(fontWeight: FontWeight.w700)),
              ),
              Text(t.statusDisplay,
                  style: TextStyle(
                      fontSize: 12,
                      color: active ? _green : _muted,
                      fontWeight: FontWeight.w700)),
            ]),
            const SizedBox(height: 4),
            Row(children: [
              if (t.isDelivery)
                const Padding(
                  padding: EdgeInsets.only(right: 6),
                  child: Text('📦', style: TextStyle(fontSize: 13)),
                ),
              Text("${money(t.price)} so'm",
                  style: const TextStyle(color: _gold, fontWeight: FontWeight.w700)),
              const Spacer(),
              Text(t.paymentStatus == 'paid' ? "To'langan" : "To'lanmagan",
                  style: TextStyle(
                      fontSize: 11,
                      color: t.paymentStatus == 'paid' ? _green : _muted)),
            ]),
            if (t.passengerName.isNotEmpty || t.passengerPhone.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                '👤 ${t.passengerName}${t.passengerPhone.isNotEmpty ? ' · ${t.passengerPhone}' : ''}',
                style: const TextStyle(color: _muted, fontSize: 13),
              ),
            ],
          ]),
        ),
      );
}

/// Marshrut qo'shish oynasi (bottom sheet).
class _AddRouteSheet extends ConsumerStatefulWidget {
  const _AddRouteSheet();

  @override
  ConsumerState<_AddRouteSheet> createState() => _AddRouteSheetState();
}

class _AddRouteSheetState extends ConsumerState<_AddRouteSheet> {
  final _a = TextEditingController();
  final _b = TextEditingController();
  final _price = TextEditingController();
  final _delivery = TextEditingController();
  final _note = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _a.dispose();
    _b.dispose();
    _price.dispose();
    _delivery.dispose();
    _note.dispose();
    super.dispose();
  }

  int? _int(String v) {
    final digits = v.replaceAll(RegExp(r'[^0-9]'), '');
    return digits.isEmpty ? null : int.tryParse(digits);
  }

  Future<void> _submit() async {
    final price = _int(_price.text);
    if (_a.text.trim().isEmpty || _b.text.trim().isEmpty || price == null) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('A punkt, B punkt va yo\'lovchi narxi majburiy.')));
      return;
    }
    setState(() => _busy = true);
    try {
      await ref.read(taxistPanelRepositoryProvider).addRoute(
            pointA: _a.text.trim(),
            pointB: _b.text.trim(),
            passengerPrice: price,
            deliveryPrice: _int(_delivery.text),
            note: _note.text.trim(),
          );
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Marshrut qo\'shishda xatolik.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, bottom + 16),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Text('Yangi marshrut',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        const SizedBox(height: 12),
        TextField(controller: _a, decoration: const InputDecoration(
            labelText: 'A punkt (qayerdan) *', hintText: 'Masalan: Shofirkon')),
        const SizedBox(height: 10),
        TextField(controller: _b, decoration: const InputDecoration(
            labelText: 'B punkt (qayerga) *', hintText: 'Masalan: Buxoro')),
        const SizedBox(height: 10),
        TextField(
          controller: _price,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(labelText: 'Yo\'lovchi narxi (so\'m) *'),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _delivery,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(
              labelText: 'Dostavka narxi (so\'m, ixtiyoriy)'),
        ),
        const SizedBox(height: 10),
        TextField(controller: _note, decoration: const InputDecoration(
            labelText: 'Izoh (ixtiyoriy)')),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: _busy ? null : _submit,
            child: Text(_busy ? 'Saqlanmoqda...' : 'Qo\'shish'),
          ),
        ),
      ]),
    );
  }
}

/// Taksist ro'yxatdan o'tish formasi.
class _TaxistRegisterForm extends ConsumerStatefulWidget {
  const _TaxistRegisterForm({required this.onDone});
  final Future<void> Function() onDone;

  @override
  ConsumerState<_TaxistRegisterForm> createState() => _TaxistRegisterFormState();
}

class _TaxistRegisterFormState extends ConsumerState<_TaxistRegisterForm> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _car = TextEditingController();
  final _region = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _car.dispose();
    _region.dispose();
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
      await ref.read(taxistPanelRepositoryProvider).register(
            fullName: _name.text.trim(),
            phone: _phone.text.trim(),
            carModel: _car.text.trim(),
            region: _region.text.trim(),
          );
      await widget.onDone();
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Ro\'yxatdan o\'tishda xatolik.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('Haydovchi bo\'lish',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        const Text(
            'Taksist sifatida ro\'yxatdan o\'ting, A→B marshrutlaringiz va narxlaringizni belgilang.',
            style: TextStyle(color: _muted)),
        const SizedBox(height: 20),
        TextField(controller: _name, decoration: const InputDecoration(
            labelText: 'Ism familiya *')),
        const SizedBox(height: 12),
        TextField(
          controller: _phone,
          keyboardType: TextInputType.phone,
          decoration: const InputDecoration(
              labelText: 'Telefon *', hintText: '+998 90 123 45 67'),
        ),
        const SizedBox(height: 12),
        TextField(controller: _car, decoration: const InputDecoration(
            labelText: 'Mashina (ixtiyoriy)', hintText: 'Chevrolet Cobalt')),
        const SizedBox(height: 12),
        TextField(controller: _region, decoration: const InputDecoration(
            labelText: 'Hudud (ixtiyoriy)', hintText: 'Shofirkon')),
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
