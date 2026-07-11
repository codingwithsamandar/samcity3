import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/providers.dart';
import 'hokim_models.dart';

/// Hokim paneli — tuman hokimi butun tuman aholisiga rasmiy e'lon yuboradi.
class HokimPanelScreen extends ConsumerStatefulWidget {
  const HokimPanelScreen({super.key});

  @override
  ConsumerState<HokimPanelScreen> createState() => _HokimPanelScreenState();
}

class _HokimPanelScreenState extends ConsumerState<HokimPanelScreen> {
  bool _loading = true;
  String? _error;
  List<HokimDistrict> _districts = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final items = await ref.read(hokimRepositoryProvider).panel();
      if (mounted) setState(() { _districts = items; _loading = false; _error = null; });
    } catch (_) {
      if (mounted) setState(() { _loading = false; _error = 'Yuklab bo\'lmadi'; });
    }
  }

  Future<void> _announce(HokimDistrict hd) async {
    final title = TextEditingController();
    final text = TextEditingController();
    XFile? picked;
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1521),
      builder: (_) => StatefulBuilder(
        builder: (context, setSheet) => Padding(
          padding: EdgeInsets.only(
              left: 16, right: 16, top: 16,
              bottom: MediaQuery.of(context).viewInsets.bottom + 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text("🏛️ ${hd.district.name} — yangi e'lon",
                style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            Text("${hd.district.residentsCount} ta aholiga yuboriladi",
                style: const TextStyle(fontSize: 12, color: Color(0xFF69748A))),
            const SizedBox(height: 12),
            TextField(controller: title, decoration: const InputDecoration(labelText: 'Sarlavha *')),
            const SizedBox(height: 8),
            TextField(controller: text, maxLines: 4, decoration: const InputDecoration(labelText: 'Matn *')),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: () async {
                final x = await ImagePicker().pickImage(source: ImageSource.gallery, imageQuality: 80);
                if (x != null) setSheet(() => picked = x);
              },
              icon: const Icon(Icons.image_outlined),
              label: Text(picked == null ? 'Rasm biriktirish (ixtiyoriy)' : '✅ Rasm tanlandi'),
            ),
            const SizedBox(height: 14),
            FilledButton.icon(
              onPressed: () => Navigator.pop(context, true),
              icon: const Icon(Icons.campaign),
              label: const Text('Butun tumanga yuborish'),
            ),
          ]),
        ),
      ),
    );
    if (ok != true || title.text.trim().isEmpty || text.text.trim().isEmpty) return;
    try {
      MultipartFile? image;
      if (picked != null) {
        image = MultipartFile.fromBytes(await picked!.readAsBytes(), filename: picked!.name);
      }
      final ann = await ref.read(hokimRepositoryProvider).announce(
          hd.district.id, title: title.text.trim(), text: text.text.trim(), image: image);
      if (!mounted) return;
      // Ma'lumotni yangilaymiz (e'lon ro'yxati + oxirgi soni).
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text("E'lon ${ann.recipientsCount} ta aholiga yuborildi ✅")));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Joylab bo\'lmadi')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('🏛️ Hokim paneli')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : _districts.isEmpty
                  ? const Center(
                      child: Padding(
                        padding: EdgeInsets.all(24),
                        child: Text("Sizda hokim paneliga ruxsat yo'q.",
                            textAlign: TextAlign.center),
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(12),
                        itemCount: _districts.length,
                        itemBuilder: (_, i) => _DistrictCard(
                            hd: _districts[i], onAnnounce: () => _announce(_districts[i])),
                      ),
                    ),
    );
  }
}

class _DistrictCard extends StatelessWidget {
  const _DistrictCard({required this.hd, required this.onAnnounce});
  final HokimDistrict hd;
  final VoidCallback onAnnounce;

  @override
  Widget build(BuildContext context) {
    final d = hd.district;
    return Card(
      margin: const EdgeInsets.only(bottom: 14),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(d.name, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Row(children: [
            _stat('${d.residentsCount}', 'Aholi'),
            const SizedBox(width: 10),
            _stat('${d.mahallasCount}', 'Mahalla'),
            const SizedBox(width: 10),
            _stat('${hd.announcements.length}', "E'lonlar"),
          ]),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: onAnnounce,
              icon: const Icon(Icons.campaign),
              label: const Text('📢 Butun tumanga e\'lon'),
            ),
          ),
          if (hd.announcements.isNotEmpty) ...[
            const SizedBox(height: 14),
            const Text("So'nggi e'lonlar",
                style: TextStyle(fontWeight: FontWeight.w700, color: Color(0xFF9AA0AC))),
            const SizedBox(height: 6),
            ...hd.announcements.take(10).map((a) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('📢 ${a.title}', style: const TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text(a.text, maxLines: 3, overflow: TextOverflow.ellipsis),
                    if (a.image != null) ...[
                      const SizedBox(height: 6),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.network(a.image!, height: 120, width: double.infinity,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => const SizedBox.shrink()),
                      ),
                    ],
                    const SizedBox(height: 2),
                    Text('${a.recipientsCount} ta aholiga yuborildi',
                        style: const TextStyle(fontSize: 11, color: Color(0xFF69748A))),
                  ]),
                )),
          ],
        ]),
      ),
    );
  }

  Widget _stat(String value, String label) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFF141B29),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(children: [
          Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF69748A))),
        ]),
      );
}
