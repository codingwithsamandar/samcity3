import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';

/// AppBar uchun qo'ng'iroq tugmasi — o'qilmaganlar soni badge bilan.
/// Bosilganda bildirishnomalar ekraniga o'tadi.
class NotificationBell extends ConsumerWidget {
  const NotificationBell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unread = ref.watch(notifControllerProvider);
    return IconButton(
      tooltip: 'Bildirishnomalar',
      onPressed: () async {
        await context.push('/notifications');
        // Qaytgach badge'ni yangilaymiz
        ref.read(notifControllerProvider.notifier).refresh();
      },
      icon: Badge(
        isLabelVisible: unread > 0,
        label: Text(unread > 99 ? '99+' : '$unread'),
        child: const Icon(Icons.notifications_outlined),
      ),
    );
  }
}
