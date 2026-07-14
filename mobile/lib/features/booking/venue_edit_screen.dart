import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/providers.dart';
import 'booking_models.dart';

const _muted = Color(0xFF9AA0AC);

const venueTypes = <String, String>{
  'wedding': "💍 To'yxona",
  'restaurant': '🍽️ Restoran',
  'barber': '💈 Sartaroshxona',
  'gym': '🏋️ Sport zal',
  'cafe': '☕ Kafe',
  'beauty': "💅 Go'zallik saloni",
  'other': '📍 Boshqa',
};

/// Joy yaratish yoki tahrirlash formasi. `venue` berilsa — tahrir rejimi.
class VenueEditScreen extends ConsumerStatefulWidget {
  const VenueEditScreen({super.key, this.venue});
  final OwnerVenue? venue;

  bool get isEdit => venue != null;

  @override
  ConsumerState<VenueEditScreen> createState() => _VenueEditScreenState();
}

class _VenueEditScreenState extends ConsumerState<VenueEditScreen> {
  late final TextEditingController _name;
  late final TextEditingController _desc;
  late final TextEditingController _address;
  late final TextEditingController _phone;
  late final TextEditingController _capacity;
  late final TextEditingController _priceDay;
  late final TextEditingController _priceHour;
  late final TextEditingController _grace;

  late String _type;
  TimeOfDay? _start;
  TimeOfDay? _end;
  bool _prepay = true;
  int _penalty = 10;
  bool _isActive = true;
  XFile? _image;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final v = widget.venue;
    _name = TextEditingController(text: v?.name ?? '');
    _desc = TextEditingController(text: v?.description ?? '');
    _address = TextEditingController(text: v?.address ?? '');
    _phone = TextEditingController(text: v?.phone ?? '');
    _capacity = TextEditingController(text: v?.capacity?.toString() ?? '');
    _priceDay = TextEditingController(text: v?.pricePerDay?.toString() ?? '');
    _priceHour = TextEditingController(text: v?.pricePerHour?.toString() ?? '');
    _grace = TextEditingController(text: (v?.graceMinutes ?? 15).toString());
    _type = v?.venueType ?? 'wedding';
    _prepay = v?.prepayRequired ?? true;
    _penalty = v?.cancelPenaltyPercent ?? 10;
    _isActive = v?.isActive ?? true;
    _start = _parseTime(v?.workingHoursStart);
    _end = _parseTime(v?.workingHoursEnd);
  }

  @override
  void dispose() {
    for (final c in [_name, _desc, _address, _phone, _capacity, _priceDay, _priceHour, _grace]) {
      c.dispose();
    }
    super.dispose();
  }

  TimeOfDay? _parseTime(String? s) {
    if (s == null || s.isEmpty) return null;
    final parts = s.split(':');
    if (parts.length < 2) return null;
    return TimeOfDay(hour: int.tryParse(parts[0]) ?? 0, minute: int.tryParse(parts[1]) ?? 0);
  }

  String? _fmt(TimeOfDay? t) =>
      t == null ? null : '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';

  int? _int(TextEditingController c) {
    final s = c.text.replaceAll(RegExp(r'[^0-9]'), '');
    return s.isEmpty ? null : int.tryParse(s);
  }

  Future<void> _pickImage() async {
    final x = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 1600);
    if (x != null) setState(() => _image = x);
  }

  Future<void> _pickTime(bool start) async {
    final t = await showTimePicker(
      context: context,
      initialTime: (start ? _start : _end) ?? const TimeOfDay(hour: 9, minute: 0),
    );
    if (t != null) setState(() => start ? _start = t : _end = t);
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Joy nomi majburiy.')));
      return;
    }
    setState(() => _busy = true);
    try {
      final data = <String, dynamic>{
        'name': _name.text.trim(),
        'venue_type': _type,
        'description': _desc.text.trim(),
        'address': _address.text.trim(),
        'phone': _phone.text.trim(),
        'prepay_required': _prepay,
        'cancel_penalty_percent': _penalty,
        'grace_minutes': _int(_grace) ?? 15,
        if (_int(_capacity) != null) 'capacity': _int(_capacity),
        if (_int(_priceDay) != null) 'price_per_day': _int(_priceDay),
        if (_int(_priceHour) != null) 'price_per_hour': _int(_priceHour),
        if (_fmt(_start) != null) 'working_hours_start': _fmt(_start),
        if (_fmt(_end) != null) 'working_hours_end': _fmt(_end),
        if (widget.isEdit) 'is_active': _isActive,
      };
      MultipartFile? img;
      if (_image != null) {
        img = MultipartFile.fromBytes(await _image!.readAsBytes(), filename: _image!.name);
      }
      final repo = ref.read(bookingRepositoryProvider);
      if (widget.isEdit) {
        await repo.updateVenue(widget.venue!.id, data, image: img);
      } else {
        await repo.createVenue(data, image: img);
      }
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Saqlashda xatolik. Maydonlarni tekshiring.')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final numFmt = [FilteringTextInputFormatter.digitsOnly];
    return Scaffold(
      appBar: AppBar(title: Text(widget.isEdit ? 'Joyni tahrirlash' : 'Yangi joy')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Rasm
          GestureDetector(
            onTap: _pickImage,
            child: Container(
              height: 150,
              decoration: BoxDecoration(
                color: const Color(0xFF141B29),
                borderRadius: BorderRadius.circular(14),
                image: _image != null
                    ? null
                    : (widget.venue?.image != null
                        ? DecorationImage(
                            image: NetworkImage(widget.venue!.image!), fit: BoxFit.cover)
                        : null),
              ),
              child: _image != null
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(14),
                      child: FutureBuilder(
                        future: _image!.readAsBytes(),
                        builder: (_, snap) => snap.hasData
                            ? Image.memory(snap.data!, fit: BoxFit.cover, width: double.infinity)
                            : const SizedBox(),
                      ),
                    )
                  : (widget.venue?.image == null
                      ? const Center(
                          child: Column(mainAxisSize: MainAxisSize.min, children: [
                          Icon(Icons.add_a_photo_outlined, color: _muted, size: 32),
                          SizedBox(height: 6),
                          Text('Rasm qo\'shish', style: TextStyle(color: _muted)),
                        ]))
                      : null),
            ),
          ),
          const SizedBox(height: 16),
          TextField(controller: _name, decoration: const InputDecoration(labelText: 'Joy nomi *')),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _type,
            decoration: const InputDecoration(labelText: 'Turi'),
            items: venueTypes.entries
                .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                .toList(),
            onChanged: (v) => setState(() => _type = v ?? 'other'),
          ),
          const SizedBox(height: 12),
          TextField(controller: _desc, maxLines: 3,
              decoration: const InputDecoration(labelText: 'Tavsif')),
          const SizedBox(height: 12),
          TextField(controller: _address, decoration: const InputDecoration(labelText: 'Manzil')),
          const SizedBox(height: 12),
          TextField(controller: _phone, keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Telefon')),
          const SizedBox(height: 12),
          TextField(controller: _capacity, keyboardType: TextInputType.number,
              inputFormatters: numFmt,
              decoration: const InputDecoration(labelText: "Sig'imi (kishi)")),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: TextField(controller: _priceDay, keyboardType: TextInputType.number,
                  inputFormatters: numFmt,
                  decoration: const InputDecoration(labelText: "Narx / kun (so'm)")),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: TextField(controller: _priceHour, keyboardType: TextInputType.number,
                  inputFormatters: numFmt,
                  decoration: const InputDecoration(labelText: "Narx / soat (so'm)")),
            ),
          ]),
          const SizedBox(height: 16),
          // Ish vaqti
          Row(children: [
            Expanded(child: _timeField('Ish boshlanishi', _start, () => _pickTime(true))),
            const SizedBox(width: 10),
            Expanded(child: _timeField('Ish tugashi', _end, () => _pickTime(false))),
          ]),
          const SizedBox(height: 8),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text("Oldindan to'lov majburiy"),
            value: _prepay,
            onChanged: (v) => setState(() => _prepay = v),
          ),
          // Bekor qilish jarimasi (0..15%)
          Row(children: [
            const Text('Bekor qilish jarimasi:'),
            Expanded(
              child: Slider(
                value: _penalty.toDouble(),
                min: 0, max: 15, divisions: 15,
                label: '$_penalty%',
                onChanged: (v) => setState(() => _penalty = v.round()),
              ),
            ),
            Text('$_penalty%', style: const TextStyle(fontWeight: FontWeight.w700)),
          ]),
          TextField(controller: _grace, keyboardType: TextInputType.number,
              inputFormatters: numFmt,
              decoration: const InputDecoration(labelText: 'Kutish vaqti (daqiqa)')),
          if (widget.isEdit)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Faol (mijozlarga ko\'rinadi)'),
              value: _isActive,
              onChanged: (v) => setState(() => _isActive = v),
            ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _busy ? null : _save,
              child: Text(_busy
                  ? 'Saqlanmoqda...'
                  : (widget.isEdit ? 'Saqlash' : 'Joy qo\'shish')),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _timeField(String label, TimeOfDay? value, VoidCallback onTap) => InkWell(
        onTap: onTap,
        child: InputDecorator(
          decoration: InputDecoration(labelText: label),
          child: Text(value == null ? '—' : _fmt(value)!,
              style: TextStyle(color: value == null ? _muted : null)),
        ),
      );
}
