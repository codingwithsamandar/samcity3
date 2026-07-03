import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../chat/chat_rooms_screen.dart';
import 'mahalla_models.dart';

/// Mahalla bo'limi — foydalanuvchi mahallasi (yoki tanlov), tab'lar bilan.
class MahallaScreen extends ConsumerStatefulWidget {
  const MahallaScreen({super.key});

  @override
  ConsumerState<MahallaScreen> createState() => _MahallaScreenState();
}

class _MahallaScreenState extends ConsumerState<MahallaScreen> {
  bool _loading = true;
  String? _selectedId;
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
        _selectedId = my ?? (items.isNotEmpty ? items.first.id : null);
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
    if (_selectedId == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Mahalla')),
        body: _all.isEmpty
            ? const Center(child: Text('Mahallalar topilmadi'))
            : ListView(
                children: _all
                    .map((n) => ListTile(
                          leading: const Icon(Icons.holiday_village_outlined),
                          title: Text(n.name),
                          subtitle: n.population != null ? Text('👥 ${n.population}') : null,
                          onTap: () => setState(() => _selectedId = n.id),
                        ))
                    .toList(),
              ),
      );
    }
    return _MahallaDetailView(
      id: _selectedId!,
      allNeighborhoods: _all,
      onSwitch: (id) => setState(() => _selectedId = id),
    );
  }
}

class _MahallaDetailView extends ConsumerStatefulWidget {
  const _MahallaDetailView({required this.id, required this.allNeighborhoods, required this.onSwitch});
  final String id;
  final List<Neighborhood> allNeighborhoods;
  final void Function(String) onSwitch;

  @override
  ConsumerState<_MahallaDetailView> createState() => _MahallaDetailViewState();
}

class _MahallaDetailViewState extends ConsumerState<_MahallaDetailView> {
  late Future<MahallaDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(mahallaRepositoryProvider).detail(widget.id);
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<MahallaDetail>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState == ConnectionState.waiting) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        if (snap.hasError) {
          return Scaffold(
              appBar: AppBar(title: const Text('Mahalla')),
              body: const Center(child: Text('Yuklab bo\'lmadi')));
        }
        final d = snap.data!;
        return DefaultTabController(
          length: 5,
          child: Scaffold(
            appBar: AppBar(
              title: Text(d.neighborhood.name),
              actions: [
                if (widget.allNeighborhoods.length > 1)
                  PopupMenuButton<String>(
                    icon: const Icon(Icons.swap_horiz),
                    onSelected: widget.onSwitch,
                    itemBuilder: (_) => widget.allNeighborhoods
                        .map((n) => PopupMenuItem(value: n.id, child: Text(n.name)))
                        .toList(),
                  ),
              ],
              bottom: const TabBar(isScrollable: true, tabs: [
                Tab(text: "Ma'lumot"),
                Tab(text: "E'lonlar"),
                Tab(text: 'Joylar'),
                Tab(text: 'Murojaat'),
                Tab(text: 'Chat'),
              ]),
            ),
            body: TabBarView(children: [
              _InfoTab(n: d.neighborhood),
              _AnnouncementsTab(items: d.announcements),
              _PlacesTab(detail: d),
              _ComplaintsTab(neighborhoodId: widget.id),
              const ChatRoomsScreen(),
            ]),
          ),
        );
      },
    );
  }
}

class _InfoTab extends StatelessWidget {
  const _InfoTab({required this.n});
  final Neighborhood n;
  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      if (n.description.isNotEmpty) ...[Text(n.description), const SizedBox(height: 16)],
      if (n.population != null) _row('👥 Aholi soni', '${n.population}'),
      if (n.headName.isNotEmpty) _row('👤 Mahalla raisi', n.headName),
      if (n.headPhone.isNotEmpty) _row('📞 Rais telefoni', n.headPhone),
    ]);
  }

  Widget _row(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(k, style: const TextStyle(color: Color(0xFF9AA6BD))),
          Text(v, style: const TextStyle(fontWeight: FontWeight.w700)),
        ]),
      );
}

class _AnnouncementsTab extends StatelessWidget {
  const _AnnouncementsTab({required this.items});
  final List<Announcement> items;
  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const Center(child: Text("E'lonlar yo'q"));
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: items.length,
      itemBuilder: (_, i) {
        final a = items[i];
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
    );
  }
}

class _PlacesTab extends StatelessWidget {
  const _PlacesTab({required this.detail});
  final MahallaDetail detail;
  @override
  Widget build(BuildContext context) {
    final children = <Widget>[];
    if (detail.stores.isNotEmpty) {
      children.add(const _Header('🛒 Do\'konlar'));
      children.addAll(detail.stores.map(_tile));
    }
    for (final g in detail.placeGroups) {
      children.add(_Header('${g.items.isNotEmpty ? g.items.first.icon : ''} ${g.label}'));
      children.addAll(g.items.map(_tile));
    }
    if (children.isEmpty) return const Center(child: Text('Bu mahallada joy topilmadi'));
    return ListView(padding: const EdgeInsets.all(8), children: children);
  }

  Widget _tile(MahallaPlace p) => ListTile(
        leading: Text(p.icon, style: const TextStyle(fontSize: 22)),
        title: Text(p.name),
        subtitle: p.address.isNotEmpty ? Text(p.address, maxLines: 1, overflow: TextOverflow.ellipsis) : null,
      );
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

class _ComplaintsTab extends ConsumerStatefulWidget {
  const _ComplaintsTab({required this.neighborhoodId});
  final String neighborhoodId;
  @override
  ConsumerState<_ComplaintsTab> createState() => _ComplaintsTabState();
}

class _ComplaintsTabState extends ConsumerState<_ComplaintsTab> {
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
      context: context, isScrollControlled: true,
      builder: (_) => _ComplaintForm(neighborhoodId: widget.neighborhoodId, cats: _cats),
    );
    if (ok == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openForm, icon: const Icon(Icons.add), label: const Text('Murojaat')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? const Center(child: Text('Murojaatlar yo\'q'))
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
