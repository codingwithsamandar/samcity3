import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'booking_models.dart';

const _muted = Color(0xFF9AA0AC);
const _green = Color(0xFF34D399);
const _gold = Color(0xFFCAA23A);

/// To'yxona/joy egasi — kelgan bronlarni tasdiqlash/bekor/yakunlash.
class VenueManageScreen extends ConsumerStatefulWidget {
  const VenueManageScreen({super.key});

  @override
  ConsumerState<VenueManageScreen> createState() => _VenueManageScreenState();
}

class _VenueManageScreenState extends ConsumerState<VenueManageScreen> {
  bool _loading = true;
  bool _busy = false;
  String? _error;
  List<VenueBooking> _pending = [];
  List<VenueBooking> _others = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final (pending, others) = await ref.read(bookingRepositoryProvider).ownerBookings();
      if (mounted) {
        setState(() { _pending = pending; _others = others; _loading = false; _error = null; });
      }
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

  Future<void> _action(VenueBooking b, String action, String label) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await ref.read(bookingRepositoryProvider).ownerAction(b.id, action);
      _toast(label);
      await _load();
    } catch (_) {
      _toast('Xatolik yuz berdi', error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('🛠️ Bronlarni boshqarish')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : (_pending.isEmpty && _others.isEmpty)
                  ? RefreshIndicator(
                      onRefresh: _load,
                      child: ListView(children: const [
                        SizedBox(height: 120),
                        Center(child: Text('Hozircha bron yo\'q.',
                            style: TextStyle(color: _muted))),
                      ]),
                    )
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView(
                        padding: const EdgeInsets.all(12),
                        children: [
                          _sectionTitle('⏳ Kutilayotgan', _pending.length),
                          if (_pending.isEmpty)
                            const Padding(
                              padding: EdgeInsets.symmetric(vertical: 8),
                              child: Text('Yangi bron yo\'q.', style: TextStyle(color: _muted)),
                            )
                          else
                            ..._pending.map((b) => _pendingCard(b)),
                          const SizedBox(height: 16),
                          if (_others.isNotEmpty) ...[
                            _sectionTitle('Boshqa bronlar', _others.length),
                            ..._others.map((b) => _historyTile(b)),
                          ],
                          const SizedBox(height: 24),
                        ],
                      ),
                    ),
    );
  }

  Widget _sectionTitle(String t, int n) => Padding(
        padding: const EdgeInsets.only(bottom: 8, top: 4),
        child: Text('$t ($n)', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
      );

  Widget _pendingCard(VenueBooking b) => Card(
        color: const Color(0xFF16202E),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(b.venueName, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            const SizedBox(height: 4),
            Text('👤 ${b.customerName.isEmpty ? "—" : b.customerName}'
                '${b.customerPhone.isNotEmpty ? " · ${b.customerPhone}" : ""}',
                style: const TextStyle(color: _muted, fontSize: 13)),
            Text('📅 ${b.bookingDate}'
                '${b.startTime != null ? " · ⏰ ${b.startTime}" : ""}'
                ' · 👥 ${b.guests}',
                style: const TextStyle(color: _muted, fontSize: 13)),
            Text('💰 ${b.amountLabel}', style: const TextStyle(color: _gold, fontSize: 13)),
            if (b.message.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text('💬 ${b.message}', style: const TextStyle(fontSize: 13),
                  maxLines: 3, overflow: TextOverflow.ellipsis),
            ],
            const SizedBox(height: 10),
            Row(children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: _busy ? null : () => _action(b, 'confirm', 'Bron tasdiqlandi ✅'),
                  icon: const Icon(Icons.check, size: 18),
                  label: const Text('Tasdiqlash'),
                ),
              ),
              const SizedBox(width: 8),
              OutlinedButton(
                onPressed: _busy ? null : () => _confirmCancel(b),
                child: const Text('Rad etish'),
              ),
            ]),
          ]),
        ),
      );

  Future<void> _confirmCancel(VenueBooking b) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Bronni rad etasizmi?'),
        content: Text('${b.venueName} · ${b.bookingDate}'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Yo\'q')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Ha, rad et')),
        ],
      ),
    );
    if (ok == true) await _action(b, 'cancel', 'Bron bekor qilindi.');
  }

  Widget _historyTile(VenueBooking b) {
    final (icon, color) = switch (b.status) {
      'confirmed' => (Icons.event_available, _green),
      'completed' => (Icons.check_circle, _gold),
      'cancelled' => (Icons.cancel, Colors.redAccent),
      'no_show' => (Icons.person_off, Colors.orangeAccent),
      _ => (Icons.event, _muted),
    };
    return Card(
      child: ListTile(
        leading: Icon(icon, color: color),
        title: Text('${b.venueName} · ${b.statusDisplay}',
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text('${b.customerName} · ${b.bookingDate} · 👥 ${b.guests}',
            maxLines: 1, overflow: TextOverflow.ellipsis),
        trailing: b.status == 'confirmed'
            ? TextButton(
                onPressed: _busy ? null : () => _action(b, 'complete', 'Bron yakunlandi.'),
                child: const Text('Yakunlash'),
              )
            : null,
      ),
    );
  }
}
