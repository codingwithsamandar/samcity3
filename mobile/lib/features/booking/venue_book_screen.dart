import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/providers.dart';
import '../delivery/delivery_models.dart' show money;
import '../payments/payment_sheet.dart';
import 'booking_models.dart';

/// Bron oqimi: xizmat → sana → vaqt → bo'sh usta → to'lov.
class VenueBookScreen extends ConsumerStatefulWidget {
  const VenueBookScreen({super.key, required this.id});
  final String id;

  @override
  ConsumerState<VenueBookScreen> createState() => _VenueBookScreenState();
}

class _VenueBookScreenState extends ConsumerState<VenueBookScreen> {
  VenueDetail? _d;
  bool _loading = true;

  String? _serviceId;
  DateTime? _date;
  List<String> _slots = [];
  String? _time;
  List<VenueStaff> _staff = [];
  String? _staffId;
  bool _loadingSlots = false, _loadingStaff = false, _submitting = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await ref.read(bookingRepositoryProvider).detail(widget.id);
      setState(() {
        _d = d;
        _loading = false;
        if (d.services.isNotEmpty) _serviceId = d.services.first.id;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  String _iso(DateTime d) => DateFormat('yyyy-MM-dd').format(d);

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context, firstDate: now,
      lastDate: now.add(const Duration(days: 365)),
      initialDate: now.add(const Duration(days: 1)),
    );
    if (picked == null) return;
    setState(() {
      _date = picked;
      _time = null;
      _staff = [];
      _staffId = null;
    });
    _loadSlots();
  }

  Future<void> _loadSlots() async {
    if (_date == null) return;
    setState(() => _loadingSlots = true);
    try {
      final s = await ref.read(bookingRepositoryProvider).slots(
            widget.id, date: _iso(_date!), service: _serviceId);
      setState(() => _slots = s);
    } catch (_) {
      setState(() => _slots = []);
    } finally {
      setState(() => _loadingSlots = false);
    }
  }

  Future<void> _pickTime(String t) async {
    setState(() {
      _time = t;
      _staff = [];
      _staffId = null;
    });
    if (_d!.staff.isEmpty) return;
    setState(() => _loadingStaff = true);
    try {
      final list = await ref.read(bookingRepositoryProvider).staffAt(
            widget.id, date: _iso(_date!), time: t, service: _serviceId);
      setState(() => _staff = list);
    } catch (_) {
      setState(() => _staff = []);
    } finally {
      setState(() => _loadingStaff = false);
    }
  }

  Future<void> _submit() async {
    final d = _d!;
    if (d.usesSlots && _serviceId == null) {
      _snack('Xizmatni tanlang');
      return;
    }
    if (_date == null) {
      _snack('Sanani tanlang');
      return;
    }
    if (d.usesSlots && _time == null) {
      _snack('Vaqtni tanlang');
      return;
    }
    if (_staff.isNotEmpty && _staffId == null) {
      _snack("Bo'sh ustani tanlang");
      return;
    }
    setState(() => _submitting = true);
    try {
      final booking = await ref.read(bookingRepositoryProvider).book(
            widget.id,
            date: _iso(_date!),
            startTime: _time,
            service: d.usesSlots ? _serviceId : null,
            staff: _staffId,
          );
      if (!mounted) return;
      // Oldindan to'lov bo'lsa — to'lov varaqasi
      if (d.prepayRequired && (booking.totalAmount ?? 0) > 0) {
        await showPaymentSheet(context, ref,
            targetType: 'booking', targetId: booking.id, title: "Bron to'lovi");
      } else {
        _snack('Bron yaratildi ✅');
      }
      if (mounted) context.go('/my-bookings');
    } catch (e) {
      _snack(e.toString().contains('409')
          ? 'Bu vaqt band. Boshqa vaqt tanlang.'
          : 'Bron yuborilmadi');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(m)));

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final d = _d;
    if (d == null) {
      return const Scaffold(body: Center(child: Text("Yuklab bo'lmadi")));
    }
    return Scaffold(
      appBar: AppBar(title: Text('Bron — ${d.venue.name}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (d.usesSlots) ..._slotFlow(d) else ..._simpleFlow(d),
          const SizedBox(height: 16),
          if (d.prepayRequired)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0x1422D3EE),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                "💳 Oldindan to'lov. Bekor qilinsa yoki kelinmasa ${d.penaltyPercent}% ushlanadi.",
                style: const TextStyle(fontSize: 12, color: Color(0xFF9AA6BD)),
              ),
            ),
          const SizedBox(height: 14),
          FilledButton.icon(
            onPressed: _submitting ? null : _submit,
            icon: _submitting
                ? const SizedBox(
                    width: 18, height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.check),
            label: Text(d.prepayRequired ? "To'lovga o'tish" : 'Bron qilish'),
          ),
        ],
      ),
    );
  }

  // ── Slot oqimi (sartarosh/salon/restoran/kafe) ──
  List<Widget> _slotFlow(VenueDetail d) {
    return [
      const _StepLabel('1. Xizmatni tanlang'),
      if (d.services.isEmpty)
        const Text("Bu joyda hozircha xizmatlar qo'shilmagan.",
            style: TextStyle(color: Color(0xFF9AA6BD)))
      else
        ...d.services.map((s) => _serviceTile(s)),
      const SizedBox(height: 16),
      const _StepLabel('2. Sana'),
      OutlinedButton.icon(
        onPressed: _pickDate,
        icon: const Icon(Icons.calendar_month),
        label: Text(_date == null ? 'Sanani tanlang' : _iso(_date!)),
      ),
      const SizedBox(height: 16),
      if (_date != null) ...[
        const _StepLabel('3. Vaqtni tanlang'),
        if (_loadingSlots)
          const Padding(padding: EdgeInsets.all(8), child: LinearProgressIndicator())
        else if (_slots.isEmpty)
          const Text("Bu kunda bo'sh vaqt yo'q.",
              style: TextStyle(color: Color(0xFF9AA6BD)))
        else
          Wrap(
            spacing: 8, runSpacing: 8,
            children: _slots.map((t) {
              final sel = t == _time;
              return ChoiceChip(
                label: Text(t),
                selected: sel,
                onSelected: (_) => _pickTime(t),
              );
            }).toList(),
          ),
        const SizedBox(height: 16),
      ],
      if (_time != null && d.staff.isNotEmpty) ...[
        const _StepLabel('4. Ustani tanlang (shu vaqtda bo\'shlari)'),
        if (_loadingStaff)
          const Padding(padding: EdgeInsets.all(8), child: LinearProgressIndicator())
        else
          ..._staff.map((s) => _staffTile(s)),
      ],
    ];
  }

  // ── Oddiy oqim (to'yxona/sport/boshqa) ──
  List<Widget> _simpleFlow(VenueDetail d) {
    return [
      const _StepLabel('Sana'),
      OutlinedButton.icon(
        onPressed: _pickDate,
        icon: const Icon(Icons.calendar_month),
        label: Text(_date == null ? 'Sanani tanlang' : _iso(_date!)),
      ),
    ];
  }

  Widget _serviceTile(VenueService s) {
    final sel = s.id == _serviceId;
    return Card(
      color: sel ? const Color(0x1434D399) : null,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: sel ? const Color(0xFF34D399) : Colors.transparent),
      ),
      child: ListTile(
        onTap: () {
          setState(() {
            _serviceId = s.id;
            _time = null;
            _staff = [];
            _staffId = null;
          });
          _loadSlots();
        },
        title: Text(s.name, style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text('${s.durationMinutes} daqiqa'),
        trailing: Text("${money(s.price)} so'm",
            style: const TextStyle(
                color: Color(0xFF34D399), fontWeight: FontWeight.w800)),
      ),
    );
  }

  Widget _staffTile(VenueStaff s) {
    final sel = s.id == _staffId;
    final busy = !s.available;
    return Opacity(
      opacity: busy ? 0.5 : 1,
      child: Card(
        color: sel ? const Color(0x1434D399) : null,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: sel ? const Color(0xFF34D399) : Colors.transparent),
        ),
        child: ListTile(
          onTap: busy ? null : () => setState(() => _staffId = s.id),
          leading: CircleAvatar(
            radius: 26,
            backgroundImage: s.photo != null ? CachedNetworkImageProvider(s.photo!) : null,
            backgroundColor: const Color(0xFF141B29),
            child: s.photo == null
                ? Text(s.name.isNotEmpty ? s.name[0] : '?')
                : null,
          ),
          title: Text(s.name, style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (s.specialty.isNotEmpty) Text(s.specialty),
              Text(
                '⭐ ${s.rating.toStringAsFixed(1)} (${s.reviewsCount}) · ✓ ${s.completedCount} ish'
                '${s.experienceYears > 0 ? ' · ${s.experienceYears} yil' : ''}',
                style: const TextStyle(fontSize: 12),
              ),
            ],
          ),
          trailing: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: busy ? const Color(0x22FB7185) : const Color(0x2234D399),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(busy ? 'Band' : "Bo'sh",
                style: TextStyle(
                    fontSize: 11, fontWeight: FontWeight.w700,
                    color: busy ? const Color(0xFFFB7185) : const Color(0xFF34D399))),
          ),
        ),
      ),
    );
  }
}

class _StepLabel extends StatelessWidget {
  const _StepLabel(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(text,
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
      );
}
