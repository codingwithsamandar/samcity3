import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../notifications/notification_bell.dart';
import 'ad_model.dart';

/// E'lonlar bosh ro'yxati — qidiruv + cheksiz scroll.
class AdsListScreen extends ConsumerStatefulWidget {
  const AdsListScreen({super.key});

  @override
  ConsumerState<AdsListScreen> createState() => _AdsListScreenState();
}

class _AdsListScreenState extends ConsumerState<AdsListScreen>
    with AutomaticKeepAliveClientMixin {
  final _search = TextEditingController();
  final _scroll = ScrollController();

  final List<AdListItem> _ads = [];
  int _page = 1;
  bool _hasNext = true;
  bool _loading = true;
  bool _loadingMore = false;
  String? _error;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_onScroll);
    _loadFirst();
  }

  void _onScroll() {
    if (!_hasNext || _loadingMore || _loading) return;
    if (_scroll.position.pixels >= _scroll.position.maxScrollExtent - 280) {
      _loadMore();
    }
  }

  Future<void> _loadFirst() async {
    setState(() {
      _loading = true;
      _error = null;
      _page = 1;
      _hasNext = true;
    });
    try {
      final page = await ref.read(adsRepositoryProvider).list(
            query: _search.text.trim(),
            page: 1,
          );
      if (!mounted) return;
      setState(() {
        _ads
          ..clear()
          ..addAll(page.items);
        _hasNext = page.hasNext;
        _page = 1;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'load';
      });
    }
  }

  Future<void> _loadMore() async {
    if (!_hasNext || _loadingMore) return;
    setState(() => _loadingMore = true);
    try {
      final nextPage = _page + 1;
      final page = await ref.read(adsRepositoryProvider).list(
            query: _search.text.trim(),
            page: nextPage,
          );
      if (!mounted) return;
      setState(() {
        _ads.addAll(page.items);
        _hasNext = page.hasNext;
        _page = nextPage;
        _loadingMore = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loadingMore = false);
    }
  }

  Future<void> _openAddAd() async {
    final created = await context.push<bool>('/ad-new');
    if (created == true) _loadFirst();
  }

  @override
  void dispose() {
    _search.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final user = ref.watch(authControllerProvider).user;
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openAddAd,
        icon: const Icon(Icons.add),
        label: const Text("E'lon"),
        backgroundColor: const Color(0xFF34D399),
        foregroundColor: const Color(0xFF04130D),
      ),
      appBar: AppBar(
        title: const Text('SamCity'),
        actions: [
          IconButton(
            tooltip: 'Xarita',
            onPressed: () => context.push('/map'),
            icon: const Icon(Icons.map_outlined),
          ),
          const NotificationBell(),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadFirst,
        child: CustomScrollView(
          controller: _scroll,
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
                child: TextField(
                  controller: _search,
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) => _loadFirst(),
                  decoration: InputDecoration(
                    hintText: 'E\'lon qidirish...',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.tune),
                      onPressed: _loadFirst,
                    ),
                  ),
                ),
              ),
            ),
            if (user != null)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
                  child: Text('Salom, ${user.displayName} 👋',
                      style: const TextStyle(color: Color(0xFF9AA6BD))),
                ),
              ),
            SliverToBoxAdapter(
              child: _QuickServices(onTap: (route) => context.push(route)),
            ),
            if (_loading)
              const SliverFillRemaining(
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              SliverFillRemaining(child: _ErrorView(onRetry: _loadFirst))
            else if (_ads.isEmpty)
              const SliverFillRemaining(
                child: Center(child: Text('E\'lon topilmadi.')),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.all(12),
                sliver: SliverGrid(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    childAspectRatio: 0.72,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                  ),
                  delegate: SliverChildBuilderDelegate(
                    (_, i) => _AdCard(ad: _ads[i]),
                    childCount: _ads.length,
                  ),
                ),
              ),
            if (_loadingMore)
              const SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Center(child: CircularProgressIndicator()),
                ),
              ),
            const SliverToBoxAdapter(child: SizedBox(height: 80)),
          ],
        ),
      ),
    );
  }
}

class _QuickServices extends StatelessWidget {
  const _QuickServices({required this.onTap});
  final void Function(String route) onTap;

  @override
  Widget build(BuildContext context) {
    const chips = [
      (Icons.work_outline, 'Ish', '/jobs'),
      (Icons.location_city_outlined, 'Joylar', '/venues'),
      (Icons.receipt_long_outlined, 'To\'lovlar', '/service-payments'),
      (Icons.groups_outlined, 'Mahalla', '/community'),
    ];
    return SizedBox(
      height: 44,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 0),
        itemCount: chips.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (_, i) {
          final (icon, label, route) = chips[i];
          return ActionChip(
            avatar: Icon(icon, size: 16, color: const Color(0xFF34D399)),
            label: Text(label, style: const TextStyle(fontSize: 12)),
            onPressed: () => onTap(route),
          );
        },
      ),
    );
  }
}

class _AdCard extends StatelessWidget {
  const _AdCard({required this.ad});
  final AdListItem ad;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => context.push('/ad/${ad.id}'),
      borderRadius: BorderRadius.circular(16),
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AspectRatio(
              aspectRatio: 16 / 11,
              child: ad.cover != null
                  ? CachedNetworkImage(
                      imageUrl: ad.cover!,
                      fit: BoxFit.cover,
                      placeholder: (_, __) =>
                          Container(color: const Color(0xFF141B29)),
                      errorWidget: (_, __, ___) =>
                          const Icon(Icons.image_not_supported),
                    )
                  : Container(
                      color: const Color(0xFF141B29),
                      child: const Icon(Icons.inventory_2_outlined,
                          size: 36, color: Color(0xFF69748A)),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.all(10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(ad.priceLabel,
                      style: const TextStyle(
                          fontWeight: FontWeight.w800, fontSize: 15)),
                  const SizedBox(height: 4),
                  Text(ad.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 13)),
                  const SizedBox(height: 4),
                  Text(ad.location.isEmpty ? 'Shahar' : ad.location,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 11, color: Color(0xFF69748A))),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.onRetry});
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off, size: 40, color: Color(0xFF69748A)),
          const SizedBox(height: 8),
          const Text('Ma\'lumotni yuklab bo\'lmadi'),
          const SizedBox(height: 8),
          OutlinedButton(onPressed: onRetry, child: const Text('Qayta urinish')),
        ],
      ),
    );
  }
}
