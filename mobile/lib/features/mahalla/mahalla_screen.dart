import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';

import '../../core/dialer.dart';
import '../../core/providers.dart';
import '../../core/shofirkon_map.dart';
import '../community/community_models.dart';
import 'mahalla_models.dart';
import 'mahalla_store_panel.dart';

/// Ovqatlanish/diqqatbop joylar toifalari (do'kon, maktab, bog'chadan tashqari).
const _diningKeys = {'restaurant', 'wedding', 'hotel'};

/// Mahalla bo'limi — avval mahalla tanlanadi, so'ng bo'limlar paneli chiqadi.
class MahallaScreen extends ConsumerStatefulWidget {
  const MahallaScreen({super.key});

  @override
  ConsumerState<MahallaScreen> createState() => _MahallaScreenState();
}

class _MahallaScreenState extends ConsumerState<MahallaScreen> {
  bool _loading = true;
  String? _myId;
  String? _selectedId; // null bo'lsa — tanlash oynasi ko'rinadi
  List<Neighborhood> _all = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final (my, items) = await ref.read(mahallaRepositoryProvider).list();
      if (!mounted) return;
      setState(() {
        _all = items;
        _myId = my;
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    // Mahalla tanlanmagan — avval tanlash oynasi.
    if (_selectedId == null) {
      return _MahallaPicker(
        all: _all,
        myId: _myId,
        onSelect: (id) => setState(() => _selectedId = id),
      );
    }
    return _MahallaHome(
      id: _selectedId!,
      isMine: _selectedId == _myId,
      onChange: () => setState(() => _selectedId = null),
    );
  }
}

// ═══════════════════════════ Tanlash oynasi ═══════════════════════════
class _MahallaPicker extends StatelessWidget {
  const _MahallaPicker({required this.all, required this.myId, required this.onSelect});
  final List<Neighborhood> all;
  final String? myId;
  final void Function(String) onSelect;

  Color _color(String hex) {
    try {
      var h = hex.replaceAll('#', '');
      if (h.length == 6) h = 'FF$h';
      return Color(int.parse(h, radix: 16));
    } catch (_) {
      return const Color(0xFF3551d1);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (all.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Mahalla')),
        body: const Center(child: Text('Mahallalar topilmadi')),
      );
    }
    // "Mening mahallam" birinchi bo'lib chiqsin.
    final ordered = [...all]..sort((a, b) {
        if (a.id == myId) return -1;
        if (b.id == myId) return 1;
        return a.name.compareTo(b.name);
      });
    return Scaffold(
      appBar: AppBar(title: const Text('Mahallangizni tanlang')),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(4, 4, 4, 12),
            child: Text('Qaysi mahalla bilan ishlamoqchisiz?',
                style: TextStyle(color: Color(0xFF9AA6BD))),
          ),
          ...ordered.map((n) {
            final mine = n.id == myId;
            final c = _color(n.color);
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: c.withValues(alpha: 0.18),
                  child: Icon(Icons.holiday_village, color: c),
                ),
                title: Row(children: [
                  Flexible(child: Text(n.name, style: const TextStyle(fontWeight: FontWeight.w800))),
                  if (mine) ...[
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: const Color(0x3334D399),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Text('Mening mahallam',
                          style: TextStyle(fontSize: 10, color: Color(0xFF34D399), fontWeight: FontWeight.w700)),
                    ),
                  ],
                ]),
                subtitle: n.population != null ? Text('👥 ${n.population} aholi') : null,
                trailing: const Icon(Icons.chevron_right),
                onTap: () => onSelect(n.id),
              ),
            );
          }),
        ],
      ),
    );
  }
}

// ═══════════════════════════ Mahalla paneli ═══════════════════════════
class _MahallaHome extends ConsumerStatefulWidget {
  const _MahallaHome({required this.id, required this.isMine, required this.onChange});
  final String id;
  final bool isMine;
  final VoidCallback onChange;

  @override
  ConsumerState<_MahallaHome> createState() => _MahallaHomeState();
}

class _MahallaHomeState extends ConsumerState<_MahallaHome> {
  late Future<MahallaDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(mahallaRepositoryProvider).detail(widget.id);
  }

  void _open(Widget page) =>
      Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<MahallaDetail>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState == ConnectionState.waiting) {
          return Scaffold(
            appBar: AppBar(title: const Text('Mahalla')),
            body: const Center(child: CircularProgressIndicator()),
          );
        }
        if (snap.hasError || !snap.hasData) {
          return Scaffold(
            appBar: AppBar(title: const Text('Mahalla')),
            body: const Center(child: Text("Yuklab bo'lmadi")),
          );
        }
        final d = snap.data!;
        final schools = d.placeGroups.where((g) => g.key == 'school').toList();
        final gardens = d.placeGroups.where((g) => g.key == 'kindergarten').toList();
        final dining = d.placeGroups.where((g) => _diningKeys.contains(g.key)).toList();
        final other = d.placeGroups
            .where((g) => g.key != 'school' && g.key != 'kindergarten' && !_diningKeys.contains(g.key))
            .toList();

        int count(List<PlaceGroup> gs) => gs.fold(0, (s, g) => s + g.items.length);

        final sections = <_Section>[
          _Section('🛒', "Do'konlar", '${d.stores.length} ta', const Color(0xFF34D399),
              () => _open(_StoresPage(detail: d))),
          _Section('🏫', 'Maktablar', '${count(schools)} ta', const Color(0xFF0284C7),
              () => _open(_PlacesPage(title: 'Maktablar', groups: schools))),
          _Section('🧸', "Bog'chalar", '${count(gardens)} ta', const Color(0xFFF472B6),
              () => _open(_PlacesPage(title: "Bog'chalar", groups: gardens))),
          _Section('🍽️', 'Ovqatlanish', '${count(dining)} ta', const Color(0xFFD97706),
              () => _open(_PlacesPage(title: 'Ovqatlanish joylari', groups: dining))),
          _Section('📍', 'Boshqa joylar', '${count(other)} ta', const Color(0xFF8B5CF6),
              () => _open(_PlacesPage(title: 'Boshqa joylar', groups: other))),
          _Section('🗺️', 'Xarita', '', const Color(0xFF22D3EE),
              () => _open(_MahallaMapPage(detail: d))),
          _Section('📢', "E'lonlar", '${d.announcements.length} ta', const Color(0xFFCAA23A),
              () => _open(_AnnouncementsPage(id: widget.id, isAdmin: d.isAdmin, items: d.announcements))),
          _Section('🗳️', "So'rovnomalar", '', const Color(0xFF7C3AED),
              () => _open(_PollsPage(neighborhoodId: widget.id))),
          _Section('🤝', 'Valentyorlik', '', const Color(0xFF16A34A),
              () => _open(_VolunteerPage(neighborhoodId: widget.id))),
          _Section('🗣️', 'Murojaat', '', const Color(0xFFFB7185),
              () => _open(_ComplaintsPage(neighborhoodId: widget.id))),
        ];

        return Scaffold(
          appBar: AppBar(
            title: Text(d.neighborhood.name),
            actions: [
              TextButton.icon(
                onPressed: widget.onChange,
                icon: const Icon(Icons.swap_horiz, size: 18),
                label: const Text("O'zgartirish"),
              ),
            ],
          ),
          body: RefreshIndicator(
            onRefresh: () async {
              setState(() => _future = ref.read(mahallaRepositoryProvider).detail(widget.id));
              await _future;
            },
            child: ListView(
              padding: const EdgeInsets.all(12),
              children: [
                _InfoCard(n: d.neighborhood, isMine: widget.isMine),
                const SizedBox(height: 12),
                const Padding(
                  padding: EdgeInsets.fromLTRB(4, 0, 4, 8),
                  child: Text("Bo'limlar", style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                ),
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  childAspectRatio: 1.5,
                  crossAxisSpacing: 10,
                  mainAxisSpacing: 10,
                  children: sections.map((s) => _SectionCard(s)).toList(),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _Section {
  final String emoji;
  final String label;
  final String hint;
  final Color color;
  final VoidCallback onTap;
  _Section(this.emoji, this.label, this.hint, this.color, this.onTap);
}

class _SectionCard extends StatelessWidget {
  const _SectionCard(this.s);
  final _Section s;
  @override
  Widget build(BuildContext context) {
    return Material(
      color: const Color(0xFF141B29),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: s.onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40, height: 40,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: s.color.withValues(alpha: 0.16),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(s.emoji, style: const TextStyle(fontSize: 20)),
              ),
              const Spacer(),
              Text(s.label, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
              if (s.hint.isNotEmpty)
                Text(s.hint, style: const TextStyle(fontSize: 12, color: Color(0xFF69748A))),
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.n, required this.isMine});
  final Neighborhood n;
  final bool isMine;
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text(isMine ? '🏠 Mening mahallam' : 'ℹ️ Mahalla',
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          ]),
          if (n.description.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(n.description, style: const TextStyle(color: Color(0xFF9AA6BD), height: 1.4)),
          ],
          const SizedBox(height: 8),
          if (n.population != null) _row('👥 Aholi soni', '${n.population}'),
          if (n.headName.isNotEmpty) _row('👤 Mahalla raisi', n.headName),
          if (n.headPhone.isNotEmpty) _row('📞 Rais telefoni', n.headPhone),
        ]),
      ),
    );
  }

  Widget _row(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(k, style: const TextStyle(color: Color(0xFF9AA6BD))),
          Flexible(child: Text(v, textAlign: TextAlign.right, style: const TextStyle(fontWeight: FontWeight.w700))),
        ]),
      );
}

// ═══════════════════════════ Do'konlar ═══════════════════════════
class _StoresPage extends ConsumerWidget {
  const _StoresPage({required this.detail});
  final MahallaDetail detail;

  Future<void> _openStoreRequest(BuildContext context, WidgetRef ref) async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1521),
      builder: (_) => _StoreRequestForm(neighborhoodId: detail.neighborhood.id),
    );
    if (ok == true && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text("Arizangiz yuborildi! Admin tasdiqlagach do'koningiz ochiladi.")));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Mahalla do'konlari"),
        actions: [
          IconButton(
            tooltip: "Do'kon egasi paneli",
            icon: const Icon(Icons.storefront),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                builder: (_) => MahallaStorePanel(neighborhoodId: detail.neighborhood.id))),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openStoreRequest(context, ref),
        icon: const Icon(Icons.add_business_outlined),
        label: const Text("Do'kon ochish"),
      ),
      body: detail.stores.isEmpty
          ? ListView(children: const [
              SizedBox(height: 100),
              Center(child: Text("Bu mahallada hali do'kon yo'q.")),
              SizedBox(height: 8),
              Center(child: Text("Do'kon ochish uchun ariza bering.",
                  style: TextStyle(color: Color(0xFF69748A)))),
            ])
          : ListView(
              padding: const EdgeInsets.all(8),
              children: [
                _OwnerBanner(neighborhoodId: detail.neighborhood.id),
                ...detail.stores.map((p) => Card(
                      child: ListTile(
                        leading: Text(p.icon, style: const TextStyle(fontSize: 24)),
                        title: Text(p.name, style: const TextStyle(fontWeight: FontWeight.w700)),
                        subtitle: p.address.isNotEmpty
                            ? Text(p.address, maxLines: 1, overflow: TextOverflow.ellipsis)
                            : null,
                        trailing: const Icon(Icons.chevron_right),
                        // store-<pk> id'dan raqamni ajratib, do'kon detaliga o'tamiz.
                        onTap: () => context.push('/store/${p.id.replaceFirst('store-', '')}'),
                      ),
                    )),
              ],
            ),
    );
  }
}

/// Do'kon egasi uchun eslatma banneri.
class _OwnerBanner extends StatelessWidget {
  const _OwnerBanner({required this.neighborhoodId});
  final String neighborhoodId;
  @override
  Widget build(BuildContext context) {
    return Card(
      color: const Color(0xFF13233A),
      child: ListTile(
        leading: const Icon(Icons.badge_outlined, color: Color(0xFF22D3EE)),
        title: const Text("Do'kon egasimisiz?", style: TextStyle(fontWeight: FontWeight.w700)),
        subtitle: const Text("Mahsulot va buyurtmalarni boshqarish paneli"),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => Navigator.of(context).push(MaterialPageRoute(
            builder: (_) => MahallaStorePanel(neighborhoodId: neighborhoodId))),
      ),
    );
  }
}

/// Mahalla do'koni ochish uchun ariza formasi (bottom sheet).
class _StoreRequestForm extends ConsumerStatefulWidget {
  const _StoreRequestForm({required this.neighborhoodId});
  final String neighborhoodId;
  @override
  ConsumerState<_StoreRequestForm> createState() => _StoreRequestFormState();
}

class _StoreRequestFormState extends ConsumerState<_StoreRequestForm> {
  final _name = TextEditingController();
  final _desc = TextEditingController();
  final _addr = TextEditingController();
  final _phone = TextEditingController();
  bool _saving = false;

  Future<void> _submit() async {
    if (_name.text.trim().isEmpty) return;
    setState(() => _saving = true);
    try {
      await ref.read(mahallaRepositoryProvider).createStoreRequest(
            widget.neighborhoodId,
            name: _name.text.trim(),
            description: _desc.text.trim(),
            address: _addr.text.trim(),
            phone: _phone.text.trim(),
          );
      if (mounted) Navigator.pop(context, true);
    } catch (_) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Yuborilmadi')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
          left: 16, right: 16, top: 16, bottom: MediaQuery.of(context).viewInsets.bottom + 16),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Text("🏘️ Mahalla do'koni ochish", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        const Text("Admin tasdiqlagach do'koningiz ochiladi (olib ketish rejimida).",
            style: TextStyle(color: Color(0xFF9AA6BD), fontSize: 12)),
        const SizedBox(height: 12),
        TextField(controller: _name, decoration: const InputDecoration(labelText: "Do'kon nomi *")),
        const SizedBox(height: 8),
        TextField(controller: _desc, maxLines: 2, decoration: const InputDecoration(labelText: 'Tavsif')),
        const SizedBox(height: 8),
        TextField(controller: _addr, decoration: const InputDecoration(labelText: 'Manzil')),
        const SizedBox(height: 8),
        TextField(controller: _phone, keyboardType: TextInputType.phone,
            decoration: const InputDecoration(labelText: 'Telefon')),
        const SizedBox(height: 14),
        FilledButton(
          onPressed: _saving ? null : _submit,
          child: _saving
              ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Ariza yuborish'),
        ),
      ]),
    );
  }
}

// ═══════════════════════════ Joylar (toifa bo'yicha) ═══════════════════════════
class _PlacesPage extends StatelessWidget {
  const _PlacesPage({required this.title, required this.groups});
  final String title;
  final List<PlaceGroup> groups;

  @override
  Widget build(BuildContext context) {
    final children = <Widget>[];
    for (final g in groups) {
      children.add(_Header('${g.icon} ${g.label}'));
      children.addAll(g.items.map((p) => Card(
            child: ListTile(
              leading: Text(p.icon, style: const TextStyle(fontSize: 22)),
              title: Text(p.name),
              subtitle: p.address.isNotEmpty
                  ? Text(p.address, maxLines: 1, overflow: TextOverflow.ellipsis)
                  : null,
            ),
          )));
    }
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: children.isEmpty
          ? const Center(child: Text("Bu bo'limda hali joy yo'q"))
          : ListView(padding: const EdgeInsets.all(8), children: children),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(8, 12, 8, 4),
        child: Text(text, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
      );
}

// ═══════════════════════════ Xarita ═══════════════════════════
class _MahallaMapPage extends StatelessWidget {
  const _MahallaMapPage({required this.detail});
  final MahallaDetail detail;

  @override
  Widget build(BuildContext context) {
    final points = <(MahallaPlace, bool)>[]; // (joy, do'konmi)
    for (final s in detail.stores) {
      if (s.lat != null && s.lng != null) points.add((s, true));
    }
    for (final g in detail.placeGroups) {
      for (final p in g.items) {
        if (p.lat != null && p.lng != null) points.add((p, false));
      }
    }
    final centroid = detail.neighborhood.centroid;
    final center = centroid != null
        ? LatLng(centroid[0], centroid[1])
        : (points.isNotEmpty
            ? LatLng(points.first.$1.lat!, points.first.$1.lng!)
            : const LatLng(40.1156, 64.5036));

    return Scaffold(
      appBar: AppBar(title: Text('${detail.neighborhood.name} — xarita')),
      body: FlutterMap(
        options: shofirkonMapOptions(center: center, zoom: 14),
        children: [
          ...basemapLayers(),
          MarkerLayer(
            markers: points.map((e) {
              final p = e.$1;
              final isStore = e.$2;
              return Marker(
                point: LatLng(p.lat!, p.lng!),
                width: 32, height: 32,
                alignment: Alignment.topCenter,
                child: GestureDetector(
                  onTap: () => showModalBottomSheet(
                    context: context,
                    backgroundColor: const Color(0xFF0F1521),
                    builder: (ctx) => Padding(
                      padding: EdgeInsets.fromLTRB(20, 20, 20, 20 + MediaQuery.of(ctx).padding.bottom),
                      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${p.icon} ${p.name}',
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                        const SizedBox(height: 4),
                        Text(isStore ? "Mahalla do'koni" : p.categoryLabel,
                            style: const TextStyle(color: Color(0xFF9AA6BD), fontSize: 12)),
                        if (p.address.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Row(children: [
                            const Icon(Icons.place, size: 16, color: Color(0xFF69748A)),
                            const SizedBox(width: 6),
                            Expanded(child: Text(p.address)),
                          ]),
                        ],
                      ]),
                    ),
                  ),
                  child: Icon(Icons.location_on,
                      size: 30, color: isStore ? const Color(0xFF34D399) : const Color(0xFF22D3EE)),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

// ═══════════════════════════ E'lonlar ═══════════════════════════
class _AnnouncementsPage extends ConsumerStatefulWidget {
  const _AnnouncementsPage({required this.id, required this.isAdmin, required this.items});
  final String id;
  final bool isAdmin;
  final List<Announcement> items;
  @override
  ConsumerState<_AnnouncementsPage> createState() => _AnnouncementsPageState();
}

class _AnnouncementsPageState extends ConsumerState<_AnnouncementsPage> {
  late List<Announcement> _items = [...widget.items];

  Future<void> _create() async {
    final title = TextEditingController();
    final text = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1521),
      builder: (_) => Padding(
        padding: EdgeInsets.only(
            left: 16, right: 16, top: 16, bottom: MediaQuery.of(context).viewInsets.bottom + 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text("📢 Yangi e'lon", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 12),
          TextField(controller: title, decoration: const InputDecoration(labelText: 'Sarlavha *')),
          const SizedBox(height: 8),
          TextField(controller: text, maxLines: 4, decoration: const InputDecoration(labelText: 'Matn *')),
          const SizedBox(height: 14),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Joylash')),
        ]),
      ),
    );
    if (ok != true || title.text.trim().isEmpty || text.text.trim().isEmpty) return;
    try {
      final a = await ref.read(mahallaRepositoryProvider)
          .createAnnouncement(widget.id, title: title.text.trim(), text: text.text.trim());
      setState(() => _items = [a, ..._items]);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Joylab bo\'lmadi')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("E'lonlar")),
      floatingActionButton: widget.isAdmin
          ? FloatingActionButton.extended(
              onPressed: _create, icon: const Icon(Icons.add), label: const Text("E'lon"))
          : null,
      body: _items.isEmpty
          ? const Center(child: Text("E'lonlar yo'q"))
          : ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _items.length,
              itemBuilder: (_, i) {
                final a = _items[i];
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('📢 ${a.title}', style: const TextStyle(fontWeight: FontWeight.w800)),
                      const SizedBox(height: 6),
                      Text(a.text),
                    ]),
                  ),
                );
              },
            ),
    );
  }
}

// ═══════════════════════════ So'rovnomalar ═══════════════════════════
class _PollsPage extends ConsumerStatefulWidget {
  const _PollsPage({required this.neighborhoodId});
  final String neighborhoodId;
  @override
  ConsumerState<_PollsPage> createState() => _PollsPageState();
}

class _PollsPageState extends ConsumerState<_PollsPage> {
  bool _loading = true;
  bool _isAdmin = false;
  List<Poll> _polls = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final (admin, items) = await ref.read(mahallaRepositoryProvider).polls(widget.neighborhoodId);
      if (mounted) setState(() { _isAdmin = admin; _polls = items; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _vote(Poll p, int optionId) async {
    try {
      final updated = await ref.read(mahallaRepositoryProvider).votePoll(p.id, [optionId]);
      setState(() => _polls = _polls.map((x) => x.id == updated.id ? updated : x).toList());
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Ovoz berib bo\'lmadi')));
      }
    }
  }

  Future<void> _create() async {
    final q = TextEditingController();
    final desc = TextEditingController();
    final opts = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1521),
      builder: (_) => Padding(
        padding: EdgeInsets.only(
            left: 16, right: 16, top: 16, bottom: MediaQuery.of(context).viewInsets.bottom + 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text("🗳️ Yangi so'rovnoma", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 4),
          const Text("Variant kiritilmasa — «Ha / Yo'q» so'rovnomasi bo'ladi.",
              style: TextStyle(color: Color(0xFF9AA6BD), fontSize: 12)),
          const SizedBox(height: 12),
          TextField(controller: q, decoration: const InputDecoration(
              labelText: 'Savol *', hintText: 'Masalan: Bepul o\'quv kurs tashkil qilaylikmi?')),
          const SizedBox(height: 8),
          TextField(controller: desc, maxLines: 2, decoration: const InputDecoration(labelText: 'Izoh')),
          const SizedBox(height: 8),
          TextField(controller: opts, maxLines: 4, decoration: const InputDecoration(
              labelText: 'Variantlar (har biri yangi qatorda)',
              hintText: 'Ha\nYo\'q\nBoshqa taklif')),
          const SizedBox(height: 14),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('So\'rovnoma ochish')),
        ]),
      ),
    );
    if (ok != true || q.text.trim().isEmpty) return;
    final options = opts.text.split('\n').map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    try {
      await ref.read(mahallaRepositoryProvider).createPoll(widget.neighborhoodId,
          question: q.text.trim(), description: desc.text.trim(), options: options);
      _load();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Ochib bo\'lmadi')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("So'rovnomalar")),
      floatingActionButton: _isAdmin
          ? FloatingActionButton.extended(
              onPressed: _create, icon: const Icon(Icons.add), label: const Text("So'rovnoma"))
          : null,
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _polls.isEmpty
              ? ListView(children: const [
                  SizedBox(height: 120),
                  Center(child: Text("Hozircha so'rovnoma yo'q")),
                ])
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(12),
                    itemCount: _polls.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (_, i) => _pollCard(_polls[i]),
                  ),
                ),
    );
  }

  Widget _pollCard(Poll p) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(p.question, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          if (p.description.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(p.description, style: const TextStyle(color: Color(0xFF9AA6BD), fontSize: 13)),
          ],
          const SizedBox(height: 10),
          ...p.options.map((o) {
            final pct = p.totalVotes > 0 ? o.votes / p.totalVotes : 0.0;
            final mine = p.myVotes.contains(o.id);
            final showResults = p.voted || !p.isOpen;
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: InkWell(
                onTap: (p.isOpen && !p.voted) ? () => _vote(p, o.id) : null,
                borderRadius: BorderRadius.circular(10),
                child: Stack(children: [
                  if (showResults)
                    Positioned.fill(
                      child: FractionallySizedBox(
                        alignment: Alignment.centerLeft,
                        widthFactor: pct.clamp(0.0, 1.0),
                        child: Container(
                          decoration: BoxDecoration(
                            color: mine ? const Color(0x3334D399) : const Color(0x22FFFFFF),
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                      ),
                    ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                    decoration: BoxDecoration(
                      border: Border.all(color: const Color(0x22FFFFFF)),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Row(children: [
                      if (mine)
                        const Padding(
                          padding: EdgeInsets.only(right: 6),
                          child: Icon(Icons.check_circle, size: 16, color: Color(0xFF34D399)),
                        ),
                      Expanded(child: Text(o.text)),
                      if (showResults)
                        Text('${(pct * 100).round()}%', style: const TextStyle(fontWeight: FontWeight.w700)),
                    ]),
                  ),
                ]),
              ),
            );
          }),
          const SizedBox(height: 8),
          Row(children: [
            Text('${p.totalVotes} ovoz · ${p.creatorName}${p.isOpen ? '' : ' · yopilgan'}',
                style: const TextStyle(fontSize: 11, color: Color(0xFF69748A))),
            const Spacer(),
            TextButton.icon(
              onPressed: () => _openComments(p),
              icon: const Icon(Icons.mode_comment_outlined, size: 16),
              label: Text('Izoh${p.commentCount > 0 ? ' (${p.commentCount})' : ''}'),
            ),
          ]),
        ]),
      ),
    );
  }

  void _openComments(Poll p) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1521),
      builder: (_) => _PollCommentsSheet(pollId: p.id),
    );
  }
}

class _PollCommentsSheet extends ConsumerStatefulWidget {
  const _PollCommentsSheet({required this.pollId});
  final String pollId;
  @override
  ConsumerState<_PollCommentsSheet> createState() => _PollCommentsSheetState();
}

class _PollCommentsSheetState extends ConsumerState<_PollCommentsSheet> {
  final _text = TextEditingController();
  bool _loading = true;
  bool _sending = false;
  List<PollComment> _items = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final items = await ref.read(mahallaRepositoryProvider).pollComments(widget.pollId);
      if (mounted) setState(() { _items = items; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _send() async {
    final t = _text.text.trim();
    if (t.isEmpty) return;
    setState(() => _sending = true);
    try {
      final items = await ref.read(mahallaRepositoryProvider).pollComments(widget.pollId, text: t);
      if (mounted) setState(() { _items = items; _text.clear(); _sending = false; });
    } catch (_) {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.6,
        maxChildSize: 0.9,
        builder: (context, controller) => Column(children: [
          const Padding(
            padding: EdgeInsets.all(14),
            child: Text('💬 Izohlar', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
          ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _items.isEmpty
                    ? const Center(child: Text('Hali izoh yo\'q'))
                    : ListView.builder(
                        controller: controller,
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        itemCount: _items.length,
                        itemBuilder: (_, i) {
                          final c = _items[i];
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 6),
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text(c.author, style: const TextStyle(
                                  fontWeight: FontWeight.w700, fontSize: 12, color: Color(0xFF9AA6BD))),
                              const SizedBox(height: 2),
                              Text(c.text),
                            ]),
                          );
                        },
                      ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
            child: Row(children: [
              Expanded(
                child: TextField(
                  controller: _text,
                  decoration: const InputDecoration(hintText: 'Izoh yozing...', isDense: true),
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                onPressed: _sending ? null : _send,
                icon: const Icon(Icons.send),
              ),
            ]),
          ),
        ]),
      ),
    );
  }
}

// ═══════════════════════════ Valentyorlik ═══════════════════════════
class _VolunteerPage extends ConsumerStatefulWidget {
  const _VolunteerPage({required this.neighborhoodId});
  final String neighborhoodId;
  @override
  ConsumerState<_VolunteerPage> createState() => _VolunteerPageState();
}

class _VolunteerPageState extends ConsumerState<_VolunteerPage> {
  bool _loading = true;
  List<HelpRequest> _items = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final items = await ref.read(mahallaRepositoryProvider).help(widget.neighborhoodId);
      if (mounted) setState(() { _items = items; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _create() async {
    final title = TextEditingController();
    final desc = TextEditingController();
    final loc = TextEditingController();
    final phone = TextEditingController();
    String kind = 'offer';
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1521),
      builder: (_) => StatefulBuilder(
        builder: (ctx, setSt) => Padding(
          padding: EdgeInsets.only(
              left: 16, right: 16, top: 16, bottom: MediaQuery.of(ctx).viewInsets.bottom + 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const Text('🤝 Ko\'ngillilik ishi', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'offer', label: Text('Yordam beraman')),
                ButtonSegment(value: 'request', label: Text('Yordam kerak')),
              ],
              selected: {kind},
              onSelectionChanged: (s) => setSt(() => kind = s.first),
            ),
            const SizedBox(height: 10),
            TextField(controller: title, decoration: const InputDecoration(labelText: 'Sarlavha *')),
            const SizedBox(height: 8),
            TextField(controller: desc, maxLines: 3, decoration: const InputDecoration(labelText: 'Tavsif *')),
            const SizedBox(height: 8),
            TextField(controller: loc, decoration: const InputDecoration(labelText: 'Manzil')),
            const SizedBox(height: 8),
            TextField(controller: phone, keyboardType: TextInputType.phone,
                decoration: const InputDecoration(labelText: 'Telefon')),
            const SizedBox(height: 14),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Yuborish')),
          ]),
        ),
      ),
    );
    if (ok != true || title.text.trim().isEmpty || desc.text.trim().isEmpty) return;
    try {
      await ref.read(mahallaRepositoryProvider).createHelp(widget.neighborhoodId,
          title: title.text.trim(), description: desc.text.trim(), kind: kind,
          location: loc.text.trim(), phone: phone.text.trim());
      _load();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Yuborilmadi')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Valentyorlik ishlari')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _create, icon: const Icon(Icons.add), label: const Text('Taklif')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? ListView(children: const [
                  SizedBox(height: 120),
                  Center(child: Text('Hozircha ko\'ngillilik ishlari yo\'q')),
                ])
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(12),
                    itemCount: _items.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) => _card(_items[i]),
                  ),
                ),
    );
  }

  Widget _card(HelpRequest h) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: const Color(0x2216A34A), borderRadius: BorderRadius.circular(8)),
              child: Text(h.categoryLabel,
                  style: const TextStyle(fontSize: 11, color: Color(0xFF34D399), fontWeight: FontWeight.w700)),
            ),
            const Spacer(),
            Text(h.kindLabel, style: const TextStyle(fontSize: 11, color: Color(0xFF69748A))),
          ]),
          const SizedBox(height: 8),
          Text(h.title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          const SizedBox(height: 4),
          Text(h.description, style: const TextStyle(color: Color(0xFF9AA6BD), fontSize: 13)),
          if (h.location.isNotEmpty || h.phone.isNotEmpty) ...[
            const SizedBox(height: 8),
            Row(children: [
              if (h.location.isNotEmpty) ...[
                const Icon(Icons.place, size: 14, color: Color(0xFF69748A)),
                const SizedBox(width: 4),
                Text(h.location, style: const TextStyle(fontSize: 12, color: Color(0xFF69748A))),
                const SizedBox(width: 12),
              ],
              if (h.phone.isNotEmpty)
                PhoneLink(h.phone, style: const TextStyle(fontSize: 12)),
            ]),
          ],
        ]),
      ),
    );
  }
}

// ═══════════════════════════ Murojaat ═══════════════════════════
class _ComplaintsPage extends ConsumerStatefulWidget {
  const _ComplaintsPage({required this.neighborhoodId});
  final String neighborhoodId;
  @override
  ConsumerState<_ComplaintsPage> createState() => _ComplaintsPageState();
}

class _ComplaintsPageState extends ConsumerState<_ComplaintsPage> {
  bool _loading = true;
  List<Complaint> _items = [];

  static const _cats = {
    'road': "Yo'l", 'water': 'Suv', 'electricity': 'Svet', 'cleaning': 'Tozalik',
    'gas': 'Gaz', 'lighting': 'Yoritilish', 'landscaping': 'Obodonlashtirish', 'other': 'Boshqa',
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final (_, items) = await ref.read(mahallaRepositoryProvider).complaints(widget.neighborhoodId);
      if (mounted) setState(() { _items = items; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openForm() async {
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1521),
      builder: (_) => _ComplaintForm(neighborhoodId: widget.neighborhoodId, cats: _cats),
    );
    if (ok == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Hokimiyatga murojaat')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openForm, icon: const Icon(Icons.add), label: const Text('Murojaat')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? const Center(child: Text("Murojaatlar yo'q"))
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: _items.length,
                  itemBuilder: (_, i) {
                    final r = _items[i];
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                            Expanded(child: Text('${r.categoryDisplay}: ${r.title}',
                                style: const TextStyle(fontWeight: FontWeight.w700))),
                            Chip(label: Text(r.statusDisplay, style: const TextStyle(fontSize: 11))),
                          ]),
                          const SizedBox(height: 4),
                          Text(r.text),
                          if (r.response.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                  color: const Color(0xFF141B29), borderRadius: BorderRadius.circular(8)),
                              child: Text('Javob: ${r.response}'),
                            ),
                          ],
                        ]),
                      ),
                    );
                  },
                ),
    );
  }
}

class _ComplaintForm extends ConsumerStatefulWidget {
  const _ComplaintForm({required this.neighborhoodId, required this.cats});
  final String neighborhoodId;
  final Map<String, String> cats;
  @override
  ConsumerState<_ComplaintForm> createState() => _ComplaintFormState();
}

class _ComplaintFormState extends ConsumerState<_ComplaintForm> {
  final _title = TextEditingController();
  final _text = TextEditingController();
  String _cat = 'road';
  bool _saving = false;

  Future<void> _submit() async {
    if (_title.text.trim().isEmpty || _text.text.trim().isEmpty) return;
    setState(() => _saving = true);
    try {
      await ref.read(mahallaRepositoryProvider).createComplaint(widget.neighborhoodId,
          category: _cat, title: _title.text.trim(), text: _text.text.trim());
      if (mounted) Navigator.pop(context, true);
    } catch (_) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Yuborilmadi')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
          left: 16, right: 16, top: 16, bottom: MediaQuery.of(context).viewInsets.bottom + 16),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const Text('🗣 Hokimiyatga murojaat', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _cat,
          items: widget.cats.entries.map((e) => DropdownMenuItem(value: e.key, child: Text(e.value))).toList(),
          onChanged: (v) => setState(() => _cat = v ?? 'road'),
          decoration: const InputDecoration(labelText: 'Turkum'),
        ),
        const SizedBox(height: 8),
        TextField(controller: _title, decoration: const InputDecoration(labelText: 'Mavzu *')),
        const SizedBox(height: 8),
        TextField(controller: _text, maxLines: 4, decoration: const InputDecoration(labelText: 'Matn *')),
        const SizedBox(height: 14),
        FilledButton(
          onPressed: _saving ? null : _submit,
          child: _saving
              ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Yuborish'),
        ),
      ]),
    );
  }
}
