import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';

/// Profil ekrani — foydalanuvchi ma'lumoti va chiqish.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Profil'),
        actions: [
          IconButton(
            tooltip: 'Chiqish',
            onPressed: () =>
                ref.read(authControllerProvider.notifier).logout(),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: user == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                const SizedBox(height: 12),
                Center(
                  child: CircleAvatar(
                    radius: 44,
                    backgroundColor: const Color(0xFF141B29),
                    backgroundImage: user.avatar != null
                        ? CachedNetworkImageProvider(user.avatar!)
                        : null,
                    child: user.avatar == null
                        ? const Icon(Icons.person, size: 44)
                        : null,
                  ),
                ),
                const SizedBox(height: 14),
                Center(
                  child: Text(user.displayName,
                      style: const TextStyle(
                          fontSize: 20, fontWeight: FontWeight.w800)),
                ),
                Center(
                  child: Text(user.phone,
                      style: const TextStyle(color: Color(0xFF9AA6BD))),
                ),
                const SizedBox(height: 8),
                Center(
                  child: TextButton.icon(
                    onPressed: () => context.push('/profile-edit'),
                    icon: const Icon(Icons.edit, size: 16),
                    label: const Text('Profilni tahrirlash'),
                  ),
                ),
                Center(
                  child: Chip(
                    avatar: const Icon(Icons.star, size: 16, color: Color(0xFFCAA23A)),
                    label: Text(user.rating.toStringAsFixed(1)),
                  ),
                ),
                const SizedBox(height: 24),
                Card(
                  child: Column(
                    children: [
                      ListTile(
                        leading: const Icon(Icons.location_city,
                            color: Color(0xFF34D399)),
                        title: const Text('Joylar (bron)'),
                        subtitle: const Text("To'yxona, restoran, salon..."),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/venues'),
                      ),
                      const Divider(height: 1),
                      ListTile(
                        leading: const Icon(Icons.event_note,
                            color: Color(0xFF22D3EE)),
                        title: const Text('Bronlarim'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/my-bookings'),
                      ),
                      const Divider(height: 1),
                      ListTile(
                        leading: const Icon(Icons.local_taxi,
                            color: Color(0xFFCAA23A)),
                        title: const Text('Sayohatlarim (taksi)'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/trips'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Card(
                  child: Column(
                    children: [
                      ListTile(
                        leading: const Icon(Icons.groups, color: Color(0xFF34D399)),
                        title: const Text('Mahalla'),
                        subtitle: const Text("So'rovnomalar va yordam markazi"),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/community'),
                      ),
                      const Divider(height: 1),
                      ListTile(
                        leading: const Icon(Icons.map, color: Color(0xFF22D3EE)),
                        title: const Text('Xarita'),
                        subtitle: const Text('Do\'kon, muassasa, joylar'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/map'),
                      ),
                      const Divider(height: 1),
                      ListTile(
                        leading: const Icon(Icons.work_outline, color: Color(0xFFCAA23A)),
                        title: const Text('Ish va rezyume'),
                        subtitle: const Text("Ish e'lonlari, rezyumelar"),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/jobs'),
                      ),
                      const Divider(height: 1),
                      ListTile(
                        leading: const Icon(Icons.receipt_long, color: Color(0xFF34D399)),
                        title: const Text("To'lovlar"),
                        subtitle: const Text('Kommunal, kurs, bog\'cha...'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/service-payments'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                // ── Biznes paneli ──
                Card(
                  child: Column(
                    children: [
                      ListTile(
                        leading: const Icon(Icons.storefront, color: Color(0xFF34D399)),
                        title: const Text("Mening do'konlarim"),
                        subtitle: const Text('Do\'kon ochish, mahsulot qo\'shish'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/my-stores'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                OutlinedButton.icon(
                  onPressed: () =>
                      ref.read(authControllerProvider.notifier).logout(),
                  icon: const Icon(Icons.logout),
                  label: const Text('Chiqish'),
                ),
              ],
            ),
    );
  }
}
