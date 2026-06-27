import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/providers.dart';

const _categories = <String, String>{
  'uy_joy': 'Uy-joy',
  'avtomobil': 'Avtomobil',
  'ish': 'Ish',
  'xizmat': 'Xizmat',
  'qishloq': "Qishloq xo'jaligi",
  'hayvonlar': 'Hayvonlar',
  'boshqa': 'Boshqa',
};

/// Yangi e'lon qo'shish formasi (rasm yuklash bilan).
class AddAdScreen extends ConsumerStatefulWidget {
  const AddAdScreen({super.key});

  @override
  ConsumerState<AddAdScreen> createState() => _AddAdScreenState();
}

class _AddAdScreenState extends ConsumerState<AddAdScreen> {
  final _form = GlobalKey<FormState>();
  final _title = TextEditingController();
  final _description = TextEditingController();
  final _price = TextEditingController();
  final _location = TextEditingController();
  final _phone = TextEditingController();

  String _category = 'boshqa';
  String _priceType = 'fixed';
  final List<XFile> _images = [];
  bool _saving = false;

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    _price.dispose();
    _location.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _pickImages() async {
    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Wrap(
          children: [
            ListTile(
              leading: const Icon(Icons.photo_library),
              title: const Text('Galereyadan tanlash'),
              onTap: () => Navigator.pop(ctx, ImageSource.gallery),
            ),
            ListTile(
              leading: const Icon(Icons.photo_camera),
              title: const Text('Kameradan olish'),
              onTap: () => Navigator.pop(ctx, ImageSource.camera),
            ),
          ],
        ),
      ),
    );
    if (source == null) return;

    final picker = ImagePicker();
    if (source == ImageSource.gallery) {
      final picked = await picker.pickMultiImage();
      if (picked.isNotEmpty) {
        setState(() => _images
          ..clear()
          ..addAll(picked.take(10)));
      }
    } else {
      final picked = await picker.pickImage(source: ImageSource.camera);
      if (picked != null) {
        setState(() => _images
          ..clear()
          ..add(picked));
      }
    }
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    if (_priceType == 'fixed') {
      final p = int.tryParse(_price.text.replaceAll(RegExp(r'\D'), ''));
      if (p == null || p <= 0) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Narx kiriting')));
        return;
      }
    }
    setState(() => _saving = true);
    try {
      final files = <MultipartFile>[];
      for (final x in _images) {
        final bytes = await x.readAsBytes();
        files.add(MultipartFile.fromBytes(bytes, filename: x.name));
      }
      await ref.read(adsRepositoryProvider).create(
            title: _title.text.trim(),
            category: _category,
            description: _description.text.trim(),
            price: _priceType == 'fixed'
                ? int.tryParse(_price.text.replaceAll(RegExp(r'\D'), ''))
                : null,
            priceType: _priceType,
            location: _location.text.trim(),
            contactPhone: _phone.text.trim(),
            images: files,
          );
      if (mounted) {
        Navigator.pop(context, true);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: const Text("E'lon joylandi! ✅"),
          backgroundColor: Colors.green.shade700,
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(_err(e)), backgroundColor: Colors.orange.shade800));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  String _err(Object e) {
    if (e is DioException) {
      final d = e.response?.data;
      if (d is Map && d.isNotEmpty) return d.values.first.toString();
    }
    return "E'lon joylanmadi. Qaytadan urinib ko'ring.";
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Yangi e'lon")),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Rasmlar
            SizedBox(
              height: 96,
              child: Row(
                children: [
                  GestureDetector(
                    onTap: _pickImages,
                    child: Container(
                      width: 96,
                      decoration: BoxDecoration(
                        color: const Color(0xFF141B29),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0x22FFFFFF)),
                      ),
                      child: const Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.add_a_photo, color: Color(0xFF34D399)),
                          SizedBox(height: 4),
                          Text('Rasm', style: TextStyle(fontSize: 12)),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _images.isEmpty
                        ? const Center(
                            child: Text('Rasm tanlanmagan',
                                style: TextStyle(color: Color(0xFF69748A))))
                        : ListView.separated(
                            scrollDirection: Axis.horizontal,
                            itemCount: _images.length,
                            separatorBuilder: (_, __) => const SizedBox(width: 8),
                            itemBuilder: (_, i) => ClipRRect(
                              borderRadius: BorderRadius.circular(10),
                              child: _Thumb(file: _images[i]),
                            ),
                          ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _title,
              decoration: const InputDecoration(labelText: 'Sarlavha *'),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Sarlavha kiriting' : null,
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _category,
              decoration: const InputDecoration(labelText: 'Kategoriya'),
              items: _categories.entries
                  .map((e) =>
                      DropdownMenuItem(value: e.key, child: Text(e.value)))
                  .toList(),
              onChanged: (v) => setState(() => _category = v ?? 'boshqa'),
            ),
            const SizedBox(height: 12),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'fixed', label: Text('Narx')),
                ButtonSegment(value: 'free', label: Text('Bepul')),
              ],
              selected: {_priceType},
              onSelectionChanged: (s) => setState(() => _priceType = s.first),
            ),
            if (_priceType == 'fixed') ...[
              const SizedBox(height: 12),
              TextFormField(
                controller: _price,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                    labelText: "Narx (so'm) *", suffixText: "so'm"),
                validator: (v) => _priceType == 'fixed' &&
                        (v == null || v.trim().isEmpty)
                    ? 'Narx kiriting'
                    : null,
              ),
            ],
            const SizedBox(height: 12),
            TextFormField(
              controller: _location,
              decoration: const InputDecoration(labelText: 'Manzil'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _phone,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(labelText: 'Aloqa telefoni'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _description,
              maxLines: 4,
              decoration: const InputDecoration(labelText: 'Tavsif'),
            ),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _saving ? null : _submit,
              child: _saving
                  ? const SizedBox(
                      height: 20, width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text("E'lonni joylash"),
            ),
          ],
        ),
      ),
    );
  }
}

class _Thumb extends StatelessWidget {
  const _Thumb({required this.file});
  final XFile file;

  @override
  Widget build(BuildContext context) {
    if (kIsWeb) {
      return Image.network(file.path, width: 96, height: 96, fit: BoxFit.cover);
    }
    return FutureBuilder(
      future: file.readAsBytes(),
      builder: (_, snap) => snap.hasData
          ? Image.memory(snap.data!, width: 96, height: 96, fit: BoxFit.cover)
          : Container(width: 96, height: 96, color: const Color(0xFF141B29)),
    );
  }
}
