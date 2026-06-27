import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/deep_link_service.dart';
import '../../core/providers.dart';
import '../ads/ads_list_screen.dart';
import '../taxi/taxists_screen.dart';
import '../delivery/stores_screen.dart';
import '../chat/chat_rooms_screen.dart';
import '../profile/profile_screen.dart';
import '../notifications/notif_socket.dart';
import 'more_services_screen.dart';

/// Asosiy ekran — pastki navigatsiya bilan bo'limlar.
class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key});

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<HomeShell> {
  int _index = 0;
  NotifSocket? _notifSocket;
  StreamSubscription<int>? _notifSub;
  StreamSubscription<Uri>? _deepLinkSub;
  final _lazyScreens = <int, Widget>{};

  Widget _screenAt(int i) {
    return _lazyScreens.putIfAbsent(i, () => switch (i) {
          0 => const AdsListScreen(),
          1 => const TaxistsScreen(),
          2 => const StoresScreen(),
          3 => const ChatRoomsScreen(),
          4 => const MoreServicesScreen(),
          5 => const ProfileScreen(),
          _ => const SizedBox.shrink(),
        });
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(cartControllerProvider.notifier).refresh();
      ref.read(notifControllerProvider.notifier).refresh();
      _connectNotifSocket();
      _listenDeepLinks();
    });
  }

  Future<void> _connectNotifSocket() async {
    _notifSub?.cancel();
    _notifSocket?.dispose();
    final socket = NotifSocket(ref.read(tokenStorageProvider));
    _notifSocket = socket;
    _notifSub = socket.unread.listen((count) {
      if (mounted) ref.read(notifControllerProvider.notifier).setCount(count);
    });
    await socket.connect();
  }

  void _listenDeepLinks() {
    final service = ref.read(deepLinkServiceProvider);
    _deepLinkSub = service.stream.listen(_handleDeepLink);
  }

  void _handleDeepLink(Uri uri) {
    if (!mounted) return;
    if (uri.scheme == 'samcity' && uri.host == 'payment-success') {
      ref.read(cartControllerProvider.notifier).refresh();
      ref.read(notifControllerProvider.notifier).refresh();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("To'lov qabul qilindi ✅")),
      );
      context.push('/orders');
      return;
    }
    if (uri.scheme == 'samcity' && uri.host == 'payment-cancel') {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("To'lov bekor qilindi")),
      );
    }
  }

  @override
  void dispose() {
    _notifSub?.cancel();
    _deepLinkSub?.cancel();
    _notifSocket?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: List.generate(6, (i) => _screenAt(i)),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.sell_outlined),
              selectedIcon: Icon(Icons.sell),
              label: "E'lonlar"),
          NavigationDestination(
              icon: Icon(Icons.local_taxi_outlined),
              selectedIcon: Icon(Icons.local_taxi),
              label: 'Taksi'),
          NavigationDestination(
              icon: Icon(Icons.delivery_dining_outlined),
              selectedIcon: Icon(Icons.delivery_dining),
              label: 'Yetkazish'),
          NavigationDestination(
              icon: Icon(Icons.forum_outlined),
              selectedIcon: Icon(Icons.forum),
              label: 'Chat'),
          NavigationDestination(
              icon: Icon(Icons.apps_outlined),
              selectedIcon: Icon(Icons.apps),
              label: "Ko'proq"),
          NavigationDestination(
              icon: Icon(Icons.person_outline),
              selectedIcon: Icon(Icons.person),
              label: 'Profil'),
        ],
      ),
    );
  }
}
