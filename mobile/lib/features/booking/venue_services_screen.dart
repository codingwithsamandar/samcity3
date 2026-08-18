import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/providers.dart';
import 'booking_models.dart';
import 'venue_edit_screen.dart';

const _muted = Color(0xFF9AA0AC);
const _green = Color(0xFF34D399);

/// Bitta joyni boshqarish: xulosa + tahrir/o'chirish + xizmat va usta CRUD.
class VenueServicesScreen extends ConsumerStatefulWidget {
  const VenueServicesScreen({super.key, required this.venueId});
  final String venueId;

  @override
  ConsumerState<VenueServicesScreen> createState() => _VenueServicesScreenState();
}

class _VenueServicesScreenState extends ConsumerState<VenueServicesScreen> {
  bool _loading = true;
  bool _busy = false;
  String? _error;
  OwnerVenue? _venue;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final v = await ref.read(bookingRepositoryProvider).ownerVenueDetail(widget.venueId);
      if (mounted) setState(() { _venue = v; _loading = false; _error = null; });
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
    } catch (_) {
      _toast('Xatolik yuz berdi', error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _edit() async {
    final changed = await Navigator.push<bool>(context,
        MaterialPageRoute(builder: (_) => VenueEditScreen(venue: _venue)));
    if (changed == true) await _load();
  }

  Future<void> _deleteVenue() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Joyni o\'chirasizmi?'),
        content: Text('${_venue!.name} — barcha xizmat, usta va bronlari bilan o\'chadi.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Yo\'q')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red.shade700),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Ha, o\'chir'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    await _guard(() async {
      await ref.read(bookingRepositoryProvider).deleteVenue(widget.venueId);
      if (mounted) {
        _toast('Joy o\'chirildi.');
        Navigator.pop(context, true);
      }
    });
  }

  Future<void> _deleteService(VenueService s) => _guard(() async {
        await ref.read(bookingRepositoryProvider).deleteService(s.id);
        await _load();
      });

  Future<void> _deleteStaff(VenueStaff s) => _guard(() async {
        await ref.read(bookingRepositoryProvider).deleteStaff(s.id);
        await _load();
      });

  Future<void> _addService() async {
    final added = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _AddServiceSheet(venueId: widget.venueId),
    );
    if (added == true) await _load();
  }

  Future<void> _addStaff() async {
    final added = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _AddStaffSheet(venueId: widget.venueId),
    );
    if (added == true) await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Joyni boshqarish')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : _buildBody(_venue!),
    );
  }

  Widget _buildBody(OwnerVenue v) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          // ── Xulosa + tahrir/o'chirish ──
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                    child: Text(v.name,
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                  ),
                  if (!v.isActive)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: Colors.orange.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Text('Nofaol',
                          style: TextStyle(color: Colors.orange, fontSize: 12)),
                    ),
                ]),
                const SizedBox(height: 4),
                Text(
                  [
                    v.venueTypeDisplay,
                    if (v.address.isNotEmpty) v.address,
                    if (v.phone.isNotEmpty) v.phone,
                  ].join(' · '),
                  style: const TextStyle(color: _muted, fontSize: 13),
                ),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _busy ? null : _edit,
                      icon: const Icon(Icons.edit_outlined, size: 18),
                      label: const Text('Tahrirlash'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _deleteVenue,
                    style: OutlinedButton.styleFrom(foregroundColor: Colors.redAccent),
                    icon: const Icon(Icons.delete_outline, size: 18),
                    label: const Text('O\'chirish'),
                  ),
                ]),
              ]),
            ),
          ),
          const SizedBox(height: 12),
          // ── Xizmatlar ──
          Row(children: [
            Expanded(child: _sectionTitle('Xizmatlar', v.services.length)),
            TextButton.icon(
              onPressed: _busy ? null : _addService,
              icon: const Icon(Icons.add, size: 18),
              label: const Text('Qo\'shish'),
            ),
          ]),
          if (v.services.isEmpty)
            _hint('Xizmat qo\'shilmagan. Masalan: «Soch olish — 30 000 so\'m».')
          else
            ...v.services.map((s) => Card(
                  child: ListTile(
                    title: Text(s.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text('${s.priceLabel} · ${s.durationMinutes} daq',
                        style: const TextStyle(fontSize: 12)),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
                      onPressed: _busy ? null : () => _deleteService(s),
                    ),
                  ),
                )),
          const SizedBox(height: 12),
          // ── Ustalar / shifokorlar (joy turiga qarab) ──
          Row(children: [
            Expanded(
                child: _sectionTitle('${v.staffLabel}lar / ishchilar', v.staff.length)),
            TextButton.icon(
              onPressed: _busy ? null : _addStaff,
              icon: const Icon(Icons.add, size: 18),
              label: const Text('Qo\'shish'),
            ),
          ]),
          if (v.staff.isEmpty)
            _hint('${v.staffLabel} qo\'shilmagan. Vaqt-slot bilan ishlaydigan '
                'joy uchun (sartarosh, salon, klinika) kiriting.')
          else
            ...v.staff.map((s) => Card(
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: const Color(0xFF141B29),
                      backgroundImage: s.photo != null ? NetworkImage(s.photo!) : null,
                      child: s.photo == null
                          ? Text(s.name.isNotEmpty ? s.name[0].toUpperCase() : '?')
                          : null,
                    ),
                    title: Text(s.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: s.specialty.isNotEmpty
                        ? Text(s.specialty, style: const TextStyle(fontSize: 12))
                        : null,
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
                      onPressed: _busy ? null : () => _deleteStaff(s),
                    ),
                  ),
                )),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _sectionTitle(String t, int n) => Padding(
        padding: const EdgeInsets.only(bottom: 4, top: 4),
        child: Text('$t ($n)', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
      );

  Widget _hint(String t) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(t, style: const TextStyle(color: _muted, fontSize: 13)),
      );
}

/// Xizmat qo'shish oynasi.
class _AddServiceSheet extends ConsumerStatefulWidget {
  const _AddServiceSheet({required this.venueId});
  final String venueId;

  @override
  ConsumerState<_AddServiceSheet> createState() => _AddServiceSheetState();
}

class _AddServiceSheetState extends ConsumerState<_AddServiceSheet> {
  final _name = TextEditingController();
  final _price = TextEditingController();
  final _dur = TextEditingController(text: '30');
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _price.dispose();
    _dur.dispose();
    super.dispose();
  }

  int? _int(TextEditingController c) {
    final s = c.text.replaceAll(RegExp(r'[^0-9]'), '');
    return s.isEmpty ? null : int.tryParse(s);
  }

  Future<void> _submit() async {
    final price = _int(_price);
    if (_name.text.trim().isEmpty || price == null || price <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Nom va to\'g\'ri narx kiriting.')));
      return;
    }
    setState(() => _busy = true);
    try {
      await ref.read(bookingRepositoryProvider).addService(
            widget.venueId,
            name: _name.text.trim(),
            price: price,
            durationMinutes: _int(_dur) ?? 30,
          );
      if (mounted) Navigator.pop(context, true);
    } catch (_) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Xizmat qo\'shishda xatolik.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, bottom + 16),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Text('Yangi xizmat',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        const SizedBox(height: 12),
        TextField(controller: _name, decoration: const InputDecoration(
            labelText: 'Xizmat nomi *', hintText: 'Masalan: Soch olish')),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(
            child: TextField(controller: _price, keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: const InputDecoration(labelText: 'Narx (so\'m) *')),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: TextField(controller: _dur, keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: const InputDecoration(labelText: 'Davomiyligi (daq)')),
          ),
        ]),
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

/// Usta/ishchi qo'shish oynasi (ixtiyoriy rasm bilan).
class _AddStaffSheet extends ConsumerStatefulWidget {
  const _AddStaffSheet({required this.venueId});
  final String venueId;

  @override
  ConsumerState<_AddStaffSheet> createState() => _AddStaffSheetState();
}

class _AddStaffSheetState extends ConsumerState<_AddStaffSheet> {
  final _name = TextEditingController();
  final _specialty = TextEditingController();
  XFile? _photo;
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _specialty.dispose();
    super.dispose();
  }

  Future<void> _pickPhoto() async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 800);
    if (x != null) setState(() => _photo = x);
  }

  Future<void> _submit() async {
    if (_name.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Ism majburiy.')));
      return;
    }
    setState(() => _busy = true);
    try {
      MultipartFile? photo;
      if (_photo != null) {
        photo = MultipartFile.fromBytes(await _photo!.readAsBytes(), filename: _photo!.name);
      }
      await ref.read(bookingRepositoryProvider).addStaff(
            widget.venueId,
            name: _name.text.trim(),
            specialty: _specialty.text.trim(),
            photo: photo,
          );
      if (mounted) Navigator.pop(context, true);
    } catch (_) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Usta qo\'shishda xatolik.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, bottom + 16),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Text('Yangi usta / ishchi',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        const SizedBox(height: 12),
        Row(children: [
          GestureDetector(
            onTap: _pickPhoto,
            child: ClipOval(
              child: Container(
                width: 56,
                height: 56,
                color: const Color(0xFF141B29),
                child: _photo == null
                    ? const Icon(Icons.add_a_photo_outlined, color: _muted, size: 22)
                    : FutureBuilder(
                        future: _photo!.readAsBytes(),
                        builder: (_, snap) => snap.hasData
                            ? Image.memory(snap.data!, fit: BoxFit.cover)
                            : const SizedBox(),
                      ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: TextField(controller: _name,
                decoration: const InputDecoration(labelText: 'Ism *')),
          ),
        ]),
        const SizedBox(height: 10),
        TextField(controller: _specialty, decoration: const InputDecoration(
            labelText: 'Mutaxassisligi', hintText: 'Masalan: Sartarosh')),
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
