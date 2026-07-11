import 'dart:typed_data';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/providers.dart';

/// Profilni tahrirlash — ism va avatar.
class ProfileEditScreen extends ConsumerStatefulWidget {
  const ProfileEditScreen({super.key});

  @override
  ConsumerState<ProfileEditScreen> createState() => _ProfileEditScreenState();
}

class _ProfileEditScreenState extends ConsumerState<ProfileEditScreen> {
  late final TextEditingController _name;
  XFile? _avatar;
  Uint8List? _avatarBytes;
  bool _saving = false;
  String _gender = '';
  DateTime? _birthDate;

  @override
  void initState() {
    super.initState();
    final user = ref.read(authControllerProvider).user;
    _name = TextEditingController(text: user?.name ?? '');
    _gender = user?.gender ?? '';
    if (user?.birthDate != null && user!.birthDate!.isNotEmpty) {
      _birthDate = DateTime.tryParse(user.birthDate!);
    }
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _pick() async {
    final img = await ImagePicker()
        .pickImage(source: ImageSource.gallery, maxWidth: 1024);
    if (img != null) {
      final bytes = await img.readAsBytes();
      setState(() {
        _avatar = img;
        _avatarBytes = bytes;
      });
    }
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      final updated = await ref.read(authRepositoryProvider).updateMe(
            name: _name.text.trim(),
            avatarBytes: _avatarBytes,
            avatarName: _avatar?.name,
            gender: _gender,
            birthDate: _birthDate == null
                ? ''
                : '${_birthDate!.year.toString().padLeft(4, '0')}-'
                    '${_birthDate!.month.toString().padLeft(2, '0')}-'
                    '${_birthDate!.day.toString().padLeft(2, '0')}',
          );
      ref.read(authControllerProvider.notifier).setUser(updated);
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: const Text('Profil yangilandi ✅'),
          backgroundColor: Colors.green.shade700,
        ));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Saqlab bo\'lmadi')));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authControllerProvider).user;
    ImageProvider? avatarImg;
    if (_avatarBytes != null) {
      avatarImg = MemoryImage(_avatarBytes!);
    } else if (user?.avatar != null) {
      avatarImg = CachedNetworkImageProvider(user!.avatar!);
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Profilni tahrirlash')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Center(
            child: Stack(
              children: [
                CircleAvatar(
                  radius: 50,
                  backgroundColor: const Color(0xFF141B29),
                  backgroundImage: avatarImg,
                  child: avatarImg == null
                      ? const Icon(Icons.person, size: 50)
                      : null,
                ),
                Positioned(
                  right: 0, bottom: 0,
                  child: GestureDetector(
                    onTap: _pick,
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: const BoxDecoration(
                        color: Color(0xFF34D399),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.camera_alt,
                          size: 18, color: Color(0xFF04130D)),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          TextField(
            controller: _name,
            decoration: const InputDecoration(labelText: 'Ism'),
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            initialValue: _gender.isEmpty ? '' : _gender,
            decoration: const InputDecoration(labelText: 'Jins'),
            items: const [
              DropdownMenuItem(value: '', child: Text("Ko'rsatilmagan")),
              DropdownMenuItem(value: 'male', child: Text('Erkak')),
              DropdownMenuItem(value: 'female', child: Text('Ayol')),
            ],
            onChanged: (v) => setState(() => _gender = v ?? ''),
          ),
          const SizedBox(height: 16),
          InkWell(
            onTap: () async {
              final now = DateTime.now();
              final picked = await showDatePicker(
                context: context,
                initialDate: _birthDate ?? DateTime(now.year - 20),
                firstDate: DateTime(now.year - 100),
                lastDate: now,
              );
              if (picked != null) setState(() => _birthDate = picked);
            },
            child: InputDecorator(
              decoration: const InputDecoration(labelText: "Tug'ilgan sana"),
              child: Text(_birthDate == null
                  ? "Tanlanmagan"
                  : '${_birthDate!.day.toString().padLeft(2, '0')}.'
                      '${_birthDate!.month.toString().padLeft(2, '0')}.${_birthDate!.year}'),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _saving ? null : _save,
            child: _saving
                ? const SizedBox(
                    height: 20, width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Saqlash'),
          ),
        ],
      ),
    );
  }
}
