import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'delivery_models.dart';

/// Markaziy katalogdan mahsulot tanlash sahifasi. Tanlangan [CatalogProduct]'ni
/// (yoki null — bekor qilinsa) qaytaradi. Do'kon egasi paneli ishlatadi.
///
/// Qidiruv: nom/brend/kategoriya nomi (server tomonda). Filtrlar: kategoriya
/// (dropdown — [categories] berilsa), o'lchov birligi (dropdown) va brend
/// (natijalardan chiqadigan chiplar).
class CatalogPickerPage extends ConsumerStatefulWidget {
  const CatalogPickerPage({super.key, this.categories = const []});

  /// [{'id': .., 'name': ..}] — MyStores javobidagi kategoriyalar (ixtiyoriy).
  final List<Map<String, dynamic>> categories;

  static Future<CatalogProduct?> show(BuildContext context,
      {List<Map<String, dynamic>> categories = const []}) {
    return Navigator.of(context).push<CatalogProduct>(
      MaterialPageRoute(builder: (_) => CatalogPickerPage(categories: categories)),
    );
  }

  @override
  ConsumerState<CatalogPickerPage> createState() => _CatalogPickerPageState();
}

/// Model UNIT_CHOICES bilan bir xil (delivery.CatalogProduct.UNIT_CHOICES).
const _units = <(String, String)>[
  ('piece', 'dona'),
  ('bottle', 'shisha'),
  ('liter', 'litr'),
  ('kg', 'kg'),
  ('gram', 'gramm'),
  ('pack', 'paket'),
  ('tray', 'fletka'),
  ('box', 'quti'),
  ('ml', 'ml'),
];

class _CatalogPickerPageState extends ConsumerState<CatalogPickerPage> {
  final _search = TextEditingController();
  final _scroll = ScrollController();
  Object? _categoryId;
  String? _unit;
  String? _brand;
  // Yuklangan natijalardan yig'ilgan brendlar — filtr chiplari uchun.
  final Set<String> _seenBrands = {};

  // Sahifalab yuklash holati: server 20 tadan qaytaradi, scroll oxirida davomi.
  final List<CatalogProduct> _items = [];
  bool _loading = true; // birinchi sahifa yuklanmoqda (ro'yxat bo'sh)
  bool _loadingMore = false;
  bool _hasMore = false;
  int _page = 1;
  int _reqId = 0; // eskirgan javoblarni tashlab yuborish uchun

  @override
  void initState() {
    super.initState();
    _scroll.addListener(() {
      if (_scroll.position.pixels >= _scroll.position.maxScrollExtent - 300) {
        _loadMore();
      }
    });
    _load();
  }

  /// Filtr/qidiruv o'zgarganda — birinchi sahifadan qayta yuklash.
  Future<void> _load() async {
    final id = ++_reqId;
    setState(() {
      _loading = true;
      _items.clear();
      _page = 1;
      _hasMore = false;
    });
    try {
      final (items, hasMore) = await _fetch(1);
      if (!mounted || id != _reqId) return;
      setState(() {
        _items.addAll(items);
        _hasMore = hasMore;
        _loading = false;
        _collectBrands(items);
      });
    } catch (_) {
      if (mounted && id == _reqId) setState(() => _loading = false);
    }
  }

  Future<void> _loadMore() async {
    if (_loading || _loadingMore || !_hasMore) return;
    final id = _reqId;
    setState(() => _loadingMore = true);
    try {
      final (items, hasMore) = await _fetch(_page + 1);
      if (!mounted || id != _reqId) return;
      setState(() {
        _page += 1;
        _items.addAll(items);
        _hasMore = hasMore;
        _loadingMore = false;
        _collectBrands(items);
      });
    } catch (_) {
      if (mounted && id == _reqId) setState(() => _loadingMore = false);
    }
  }

  Future<(List<CatalogProduct>, bool)> _fetch(int page) {
    return ref.read(deliveryRepositoryProvider).catalog(
          search: _search.text.trim(),
          categoryId: _categoryId,
          brand: _brand,
          unit: _unit,
          page: page,
        );
  }

  void _collectBrands(List<CatalogProduct> items) {
    // Brend filtri tanlangan holatda yig'maymiz — chiplar to'plami torayib qolmasin.
    if (_brand != null) return;
    _seenBrands.addAll(items.map((c) => c.brand).where((b) => b.isNotEmpty));
  }

  @override
  void dispose() {
    _search.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Katalogdan tanlash')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
            child: TextField(
              controller: _search,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _load(),
              decoration: InputDecoration(
                hintText: "Nom, brend yoki kategoriya bo'yicha qidirish",
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(icon: const Icon(Icons.arrow_forward), onPressed: _load),
              ),
            ),
          ),
          // ── Filtrlar: kategoriya + birlik ──
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Row(children: [
              if (widget.categories.isNotEmpty)
                Expanded(
                  child: DropdownButtonFormField<Object?>(
                    initialValue: _categoryId,
                    isExpanded: true,
                    decoration: const InputDecoration(
                        labelText: 'Kategoriya', isDense: true, border: OutlineInputBorder()),
                    items: [
                      const DropdownMenuItem<Object?>(value: null, child: Text('Barchasi')),
                      ...widget.categories.map((c) => DropdownMenuItem<Object?>(
                          value: c['id'], child: Text('${c['name']}', overflow: TextOverflow.ellipsis))),
                    ],
                    onChanged: (v) {
                      _categoryId = v;
                      _load();
                    },
                  ),
                ),
              if (widget.categories.isNotEmpty) const SizedBox(width: 8),
              Expanded(
                child: DropdownButtonFormField<String?>(
                  initialValue: _unit,
                  isExpanded: true,
                  decoration: const InputDecoration(
                      labelText: 'Birlik', isDense: true, border: OutlineInputBorder()),
                  items: [
                    const DropdownMenuItem<String?>(value: null, child: Text('Barchasi')),
                    ..._units.map((u) =>
                        DropdownMenuItem<String?>(value: u.$1, child: Text(u.$2))),
                  ],
                  onChanged: (v) {
                    _unit = v;
                    _load();
                  },
                ),
              ),
            ]),
          ),
          // ── Brend chiplari (yuklangan natijalardan) ──
          if (_seenBrands.isNotEmpty || _brand != null)
            SizedBox(
              height: 44,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                children: [
                  for (final b in _seenBrands.toList()..sort())
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: FilterChip(
                        label: Text(b, style: const TextStyle(fontSize: 12)),
                        selected: _brand == b,
                        onSelected: (sel) {
                          _brand = sel ? b : null;
                          _load();
                        },
                      ),
                    ),
                ],
              ),
            ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _items.isEmpty
                    ? const Center(child: Text("Katalog bo'sh yoki topilmadi"))
                    : ListView.separated(
                        controller: _scroll,
                        // +1: oxirida "yuklanmoqda" qatori (davomi bo'lsa).
                        itemCount: _items.length + (_hasMore ? 1 : 0),
                        separatorBuilder: (_, __) => const Divider(height: 1),
                        itemBuilder: (_, i) {
                          if (i >= _items.length) {
                            // Build ichida setState bo'lmasligi uchun keyingi kadrga.
                            WidgetsBinding.instance
                                .addPostFrameCallback((_) => _loadMore());
                            return const Padding(
                              padding: EdgeInsets.symmetric(vertical: 14),
                              child: Center(
                                  child: SizedBox(
                                      width: 22, height: 22,
                                      child: CircularProgressIndicator(strokeWidth: 2.4))),
                            );
                          }
                          final c = _items[i];
                          final sub = [
                            if (c.brand.isNotEmpty) c.brand,
                            if (c.category != null) c.category!,
                            if (c.unitDisplay.isNotEmpty) c.unitDisplay,
                          ].join(' · ');
                          return ListTile(
                            leading: c.image != null
                                ? ClipRRect(
                                    borderRadius: BorderRadius.circular(8),
                                    child: Image.network(c.image!, width: 44, height: 44, fit: BoxFit.cover,
                                        errorBuilder: (_, __, ___) => const Icon(Icons.inventory_2_outlined)))
                                : const Icon(Icons.inventory_2_outlined, size: 32),
                            title: Text(c.name),
                            subtitle: sub.isEmpty ? null : Text(sub),
                            onTap: () => Navigator.of(context).pop(c),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}

/// Tanlangan katalog mahsulotining ko'rinishi (rasm + brend + o'lchov birligi).
/// Mahsulot qo'shish sheet'ida katalog tanlangach ko'rsatiladi.
class CatalogPreviewTile extends StatelessWidget {
  const CatalogPreviewTile({super.key, required this.product});
  final CatalogProduct product;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0x1134D399),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(children: [
        if (product.image != null)
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: Image.network(product.image!, width: 48, height: 48, fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => const Icon(Icons.inventory_2_outlined, size: 36)),
          )
        else
          const Icon(Icons.inventory_2_outlined, size: 36, color: Color(0xFF9AA6BD)),
        const SizedBox(width: 10),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(product.name,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                maxLines: 1, overflow: TextOverflow.ellipsis),
            const SizedBox(height: 2),
            Text(
              [
                if (product.brand.isNotEmpty) product.brand,
                if (product.unitDisplay.isNotEmpty) "o'lchov: ${product.unitDisplay}",
              ].join(' · '),
              style: const TextStyle(fontSize: 11.5, color: Color(0xFF9AA6BD)),
              maxLines: 1, overflow: TextOverflow.ellipsis,
            ),
          ]),
        ),
      ]),
    );
  }
}

/// Mahalla do'koni ko'rsatkichlari: "O'z mahsulotlari: X/10 · Katalogdan: Y".
class StoreCatalogStats extends StatelessWidget {
  const StoreCatalogStats({super.key, required this.store});
  final Store store;

  @override
  Widget build(BuildContext context) {
    final used = store.customProductCount;
    final limit = store.customLimit;
    final cat = store.catalogProductCount;
    if (used == null && cat == null) return const SizedBox.shrink();
    final full = limit != null && (used ?? 0) >= limit;
    Widget chip(String text, Color color) => Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: color.withValues(alpha: .13),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(text,
              style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w700)),
        );
    return Wrap(spacing: 6, runSpacing: 4, children: [
      if (used != null && limit != null)
        chip("O'z mahsulotlari: $used / $limit",
            full ? const Color(0xFFFB7185) : const Color(0xFFCAA23A)),
      if (cat != null) chip('Katalogdan: $cat', const Color(0xFF34D399)),
    ]);
  }
}
