import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'community_models.dart';

/// Mahalla — so'rovnomalar va yordam markazi.
class CommunityScreen extends ConsumerWidget {
  const CommunityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Mahalla'),
          bottom: const TabBar(tabs: [
            Tab(text: "So'rovnomalar"),
            Tab(text: 'Yordam'),
          ]),
        ),
        body: const TabBarView(children: [_PollsTab(), _HelpTab()]),
      ),
    );
  }
}

// ─────────────────────── So'rovnomalar ───────────────────────
class _PollsTab extends ConsumerStatefulWidget {
  const _PollsTab();
  @override
  ConsumerState<_PollsTab> createState() => _PollsTabState();
}

class _PollsTabState extends ConsumerState<_PollsTab> {
  late Future<List<Poll>> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(communityRepositoryProvider).polls();
  }

  void _reload() =>
      setState(() => _future = ref.read(communityRepositoryProvider).polls());

  Future<void> _vote(Poll p, int optionId) async {
    try {
      await ref.read(communityRepositoryProvider).vote(p.id, [optionId]);
      _reload();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Ovoz berib bo\'lmadi')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async => _reload(),
      child: FutureBuilder<List<Poll>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final polls = snap.data ?? [];
          if (polls.isEmpty) {
            return ListView(children: const [
              SizedBox(height: 120),
              Center(child: Text("Hozircha so'rovnoma yo'q")),
            ]);
          }
          return ListView.separated(
            padding: const EdgeInsets.all(12),
            itemCount: polls.length,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (_, i) => _pollCard(polls[i]),
          );
        },
      ),
    );
  }

  Widget _pollCard(Poll p) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(p.question,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
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
                  child: Stack(
                    children: [
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
                        child: Row(
                          children: [
                            if (mine)
                              const Padding(
                                padding: EdgeInsets.only(right: 6),
                                child: Icon(Icons.check_circle, size: 16, color: Color(0xFF34D399)),
                              ),
                            Expanded(child: Text(o.text)),
                            if (showResults)
                              Text('${(pct * 100).round()}%',
                                  style: const TextStyle(fontWeight: FontWeight.w700)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
            const SizedBox(height: 8),
            Text('${p.totalVotes} ovoz · ${p.creatorName}${p.isOpen ? '' : ' · yopilgan'}',
                style: const TextStyle(fontSize: 11, color: Color(0xFF69748A))),
          ],
        ),
      ),
    );
  }
}

// ─────────────────────── Yordam markazi ───────────────────────
class _HelpTab extends ConsumerStatefulWidget {
  const _HelpTab();
  @override
  ConsumerState<_HelpTab> createState() => _HelpTabState();
}

class _HelpTabState extends ConsumerState<_HelpTab> {
  Future<(List<HelpCategory>, List<HelpRequest>)>? _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(communityRepositoryProvider).help();
  }

  void _reload() =>
      setState(() => _future = ref.read(communityRepositoryProvider).help());

  Future<void> _create() async {
    final title = TextEditingController();
    final desc = TextEditingController();
    final loc = TextEditingController();
    final phone = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1521),
      builder: (_) => Padding(
        padding: EdgeInsets.only(
          left: 16, right: 16, top: 16,
          bottom: MediaQuery.of(context).viewInsets.bottom + 16,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text("Yordam so'rovi", style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            TextField(controller: title, decoration: const InputDecoration(labelText: 'Sarlavha *')),
            const SizedBox(height: 10),
            TextField(controller: desc, maxLines: 3, decoration: const InputDecoration(labelText: 'Tavsif *')),
            const SizedBox(height: 10),
            TextField(controller: loc, decoration: const InputDecoration(labelText: 'Manzil')),
            const SizedBox(height: 10),
            TextField(controller: phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Telefon')),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Yuborish'),
            ),
          ],
        ),
      ),
    );
    if (ok != true) return;
    if (title.text.trim().isEmpty || desc.text.trim().isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Sarlavha va tavsif majburiy')));
      }
      return;
    }
    try {
      await ref.read(communityRepositoryProvider).createHelp(
            title: title.text.trim(), description: desc.text.trim(),
            location: loc.text.trim(), phone: phone.text.trim());
      _reload();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Yuborilmadi')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _create,
        icon: const Icon(Icons.add),
        label: const Text("So'rov"),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<(List<HelpCategory>, List<HelpRequest>)>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            final items = snap.data?.$2 ?? [];
            if (items.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: Text("Hozircha yordam so'rovlari yo'q")),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _helpCard(items[i]),
            );
          },
        ),
      ),
    );
  }

  Widget _helpCard(HelpRequest h) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0x2222D3EE),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(h.categoryLabel,
                    style: const TextStyle(fontSize: 11, color: Color(0xFF22D3EE), fontWeight: FontWeight.w700)),
              ),
              const SizedBox(width: 6),
              if (h.isUrgent)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0x22FB7185),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text('Shoshilinch',
                      style: TextStyle(fontSize: 11, color: Color(0xFFFB7185), fontWeight: FontWeight.w700)),
                ),
              const Spacer(),
              Text(h.kindLabel, style: const TextStyle(fontSize: 11, color: Color(0xFF69748A))),
            ]),
            const SizedBox(height: 8),
            Text(h.title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            const SizedBox(height: 4),
            Text(h.description, style: const TextStyle(color: Color(0xFF9AA6BD), fontSize: 13)),
            const SizedBox(height: 8),
            Row(children: [
              if (h.location.isNotEmpty) ...[
                const Icon(Icons.place, size: 14, color: Color(0xFF69748A)),
                const SizedBox(width: 4),
                Text(h.location, style: const TextStyle(fontSize: 12, color: Color(0xFF69748A))),
                const SizedBox(width: 12),
              ],
              if (h.phone.isNotEmpty) ...[
                const Icon(Icons.phone, size: 14, color: Color(0xFF69748A)),
                const SizedBox(width: 4),
                Text(h.phone, style: const TextStyle(fontSize: 12, color: Color(0xFF69748A))),
              ],
            ]),
          ],
        ),
      ),
    );
  }
}
