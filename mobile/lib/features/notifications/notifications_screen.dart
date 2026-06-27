import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/providers.dart';
import 'notification_model.dart';

/// Bildirishnomalar ro'yxati ekrani.
class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  late Future<NotificationPage> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<NotificationPage> _load() =>
      ref.read(notificationsRepositoryProvider).list();

  void _reload() {
    setState(() => _future = _load());
    // Badge sonini ham yangilaymiz
    ref.read(notifControllerProvider.notifier).refresh();
  }

  Future<void> _markAll() async {
    await ref.read(notificationsRepositoryProvider).markRead();
    _reload();
  }

  Future<void> _tapOne(AppNotification n) async {
    if (!n.isRead) {
      await ref.read(notificationsRepositoryProvider).markRead(ids: [n.id]);
      _reload();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Bildirishnomalar'),
        actions: [
          IconButton(
            tooltip: 'Hammasini o\'qildi',
            onPressed: _markAll,
            icon: const Icon(Icons.done_all),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<NotificationPage>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: Text('Yuklab bo\'lmadi. Pastga torting.')),
              ]);
            }
            final items = snap.data?.items ?? [];
            if (items.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(
                  child: Column(children: [
                    Icon(Icons.notifications_off_outlined,
                        size: 48, color: Color(0xFF69748A)),
                    SizedBox(height: 8),
                    Text('Hozircha bildirishnoma yo\'q'),
                  ]),
                ),
              ]);
            }
            return ListView.separated(
              itemCount: items.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) => _NotifTile(n: items[i], onTap: () => _tapOne(items[i])),
            );
          },
        ),
      ),
    );
  }
}

class _NotifTile extends StatelessWidget {
  const _NotifTile({required this.n, required this.onTap});
  final AppNotification n;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      onTap: onTap,
      leading: CircleAvatar(
        backgroundColor: const Color(0xFF141B29),
        child: Text(n.icon, style: const TextStyle(fontSize: 18)),
      ),
      title: Text(
        n.text,
        style: TextStyle(
          fontWeight: n.isRead ? FontWeight.w400 : FontWeight.w700,
        ),
      ),
      subtitle: n.createdAt != null
          ? Text(DateFormat('dd.MM.yyyy HH:mm').format(n.createdAt!.toLocal()),
              style: const TextStyle(fontSize: 11, color: Color(0xFF69748A)))
          : null,
      trailing: n.isRead
          ? null
          : Container(
              width: 10,
              height: 10,
              decoration: const BoxDecoration(
                color: Color(0xFF34D399),
                shape: BoxShape.circle,
              ),
            ),
    );
  }
}
