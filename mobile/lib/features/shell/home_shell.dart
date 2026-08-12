import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/feature_flags.dart';
import '../../core/providers.dart';
import '../ads/ads_list_screen.dart';
import '../taxi/taxists_screen.dart';
import '../delivery/stores_screen.dart';
import '../mahalla/mahalla_screen.dart';
import '../profile/profile_screen.dart';
import '../notifications/notif_socket.dart';
import 'more_services_screen.dart';

/// Asosiy ekran — pastki navigatsiya bilan bo'limlar.
class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key});

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

/// Bitta pastki navigatsiya tabi.
class _Tab {
  const _Tab(this.icon, this.selectedIcon, this.label, this.build);
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final Widget Function() build;
}

class _HomeShellState extends ConsumerState<HomeShell> {
  int _index = 0;
  NotifSocket? _notifSocket;
  StreamSubscription<int>? _notifSub;
  StreamSubscription<Uri>? _deepLinkSub;
  final _lazyScreens = <int, Widget>{};

  /// Tablar ro'yxati. Taksi arxivlangan (kTaxiEnabled=false) — o'sha tab
  /// ro'yxatga qo'shilmaydi, qolgan indekslar avtomatik siljiydi.
  static final List<_Tab> _tabs = [
    _Tab(Icons.sell_outlined, Icons.sell, "E'lonlar",
        () => const AdsListScreen()),
    if (kTaxiEnabled)
      _Tab(Icons.local_taxi_outlined, Icons.local_taxi, 'Taksi',
          () => const TaxistsScreen()),
    _Tab(Icons.delivery_dining_outlined, Icons.delivery_dining, 'Yetkazish',
        () => const StoresScreen()),
    _Tab(Icons.holiday_village_outlined, Icons.holiday_village, 'Mahalla',
        () => const MahallaScreen()),
    _Tab(Icons.apps_outlined, Icons.apps, "Ko'proq",
        () => const MoreServicesScreen()),
    _Tab(Icons.person_outline, Icons.person, 'Profil',
        () => const ProfileScreen()),
  ];

  Widget _screenAt(int i) {
    return _lazyScreens.putIfAbsent(
        i, () => i < _tabs.length ? _tabs[i].build() : const SizedBox.shrink());
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
        children: List.generate(_tabs.length, (i) => _screenAt(i)),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          for (final t in _tabs)
            NavigationDestination(
                icon: Icon(t.icon),
                selectedIcon: Icon(t.selectedIcon),
                label: t.label),
        ],
      ),
    );
  }
}
