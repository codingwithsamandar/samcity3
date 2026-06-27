import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/providers.dart';
import 'jobs_models.dart';

/// Ish va rezyume bo'limi (2 tab).
class JobsScreen extends ConsumerWidget {
  const JobsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Ish va rezyume'),
          bottom: const TabBar(tabs: [Tab(text: 'Ishlar'), Tab(text: 'Rezyumelar')]),
        ),
        body: const TabBarView(children: [_JobsTab(), _ResumesTab()]),
      ),
    );
  }
}

Future<void> _call(String phone) async {
  if (phone.isEmpty) return;
  await launchUrl(Uri.parse('tel:$phone'));
}

// ─────────── Ishlar ───────────
class _JobsTab extends ConsumerStatefulWidget {
  const _JobsTab();
  @override
  ConsumerState<_JobsTab> createState() => _JobsTabState();
}

class _JobsTabState extends ConsumerState<_JobsTab> {
  late Future<List<JobAd>> _future;
  @override
  void initState() {
    super.initState();
    _future = ref.read(jobsRepositoryProvider).jobs();
  }

  void _reload() => setState(() => _future = ref.read(jobsRepositoryProvider).jobs());

  Future<void> _create() async {
    final ok = await _showCreateSheet(context, isJob: true, ref: ref);
    if (ok == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _create, icon: const Icon(Icons.add), label: const Text('Ish'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<List<JobAd>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            final jobs = snap.data ?? [];
            if (jobs.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 120), Center(child: Text("Ish e'lonlari yo'q"))]);
            }
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: jobs.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _jobCard(jobs[i]),
            );
          },
        ),
      ),
    );
  }

  Widget _jobCard(JobAd j) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(j.title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
              const SizedBox(height: 2),
              Text('${j.company} · ${j.jobTypeLabel}',
                  style: const TextStyle(color: Color(0xFF9AA6BD), fontSize: 13)),
              const SizedBox(height: 6),
              Text(j.salaryLabel,
                  style: const TextStyle(color: Color(0xFF34D399), fontWeight: FontWeight.w700)),
              if (j.location.isNotEmpty) ...[
                const SizedBox(height: 4),
                Row(children: [
                  const Icon(Icons.place, size: 14, color: Color(0xFF69748A)),
                  const SizedBox(width: 4),
                  Text(j.location, style: const TextStyle(fontSize: 12, color: Color(0xFF69748A))),
                ]),
              ],
              if (j.description.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(j.description, maxLines: 3, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13)),
              ],
              if (j.contactPhone.isNotEmpty) ...[
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => _call(j.contactPhone),
                  icon: const Icon(Icons.phone, size: 16),
                  label: Text(j.contactPhone),
                ),
              ],
            ],
          ),
        ),
      );
}

// ─────────── Rezyumelar ───────────
class _ResumesTab extends ConsumerStatefulWidget {
  const _ResumesTab();
  @override
  ConsumerState<_ResumesTab> createState() => _ResumesTabState();
}

class _ResumesTabState extends ConsumerState<_ResumesTab> {
  late Future<List<ResumeAd>> _future;
  @override
  void initState() {
    super.initState();
    _future = ref.read(jobsRepositoryProvider).resumes();
  }

  void _reload() => setState(() => _future = ref.read(jobsRepositoryProvider).resumes());

  Future<void> _create() async {
    final ok = await _showCreateSheet(context, isJob: false, ref: ref);
    if (ok == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _create, icon: const Icon(Icons.add), label: const Text('Rezyume'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<List<ResumeAd>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            final list = snap.data ?? [];
            if (list.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 120), Center(child: Text("Rezyumelar yo'q"))]);
            }
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: list.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _resumeCard(list[i]),
            );
          },
        ),
      ),
    );
  }

  Widget _resumeCard(ResumeAd r) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(r.title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
              const SizedBox(height: 2),
              Text('Tajriba: ${r.experienceLabel}',
                  style: const TextStyle(color: Color(0xFF9AA6BD), fontSize: 13)),
              const SizedBox(height: 6),
              Text(r.salaryLabel,
                  style: const TextStyle(color: Color(0xFF34D399), fontWeight: FontWeight.w700)),
              if (r.skills.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text('Ko\'nikmalar: ${r.skills}',
                    maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12, color: Color(0xFF9AA6BD))),
              ],
              if (r.about.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(r.about, maxLines: 3, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13)),
              ],
              if (r.contactPhone.isNotEmpty) ...[
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => _call(r.contactPhone),
                  icon: const Icon(Icons.phone, size: 16),
                  label: Text(r.contactPhone),
                ),
              ],
            ],
          ),
        ),
      );
}

// ─────────── Yaratish varaqasi (ish yoki rezyume) ───────────
Future<bool?> _showCreateSheet(BuildContext context,
    {required bool isJob, required WidgetRef ref}) {
  final title = TextEditingController();
  final second = TextEditingController(); // kompaniya (ish) / ko'nikmalar (rezyume)
  final body = TextEditingController();
  final salary = TextEditingController();
  final loc = TextEditingController();
  bool busy = false;

  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    backgroundColor: const Color(0xFF0F1521),
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setSt) => Padding(
        padding: EdgeInsets.only(
          left: 16, right: 16, top: 16,
          bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(isJob ? "Ish e'loni" : 'Rezyume',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            TextField(controller: title, decoration: InputDecoration(
                labelText: isJob ? 'Lavozim *' : 'Kasb nomi *')),
            const SizedBox(height: 10),
            TextField(controller: second, decoration: InputDecoration(
                labelText: isJob ? 'Kompaniya *' : "Ko'nikmalar")),
            const SizedBox(height: 10),
            TextField(controller: body, maxLines: 3, decoration: InputDecoration(
                labelText: isJob ? 'Tavsif *' : "O'zingiz haqingizda *")),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: TextField(controller: salary,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Maosh (so\'m)'))),
              const SizedBox(width: 10),
              Expanded(child: TextField(controller: loc,
                  decoration: const InputDecoration(labelText: 'Manzil'))),
            ]),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: busy ? null : () async {
                if (title.text.trim().isEmpty || body.text.trim().isEmpty ||
                    (isJob && second.text.trim().isEmpty)) {
                  ScaffoldMessenger.of(ctx).showSnackBar(
                      const SnackBar(content: Text('Majburiy maydonlarni to\'ldiring')));
                  return;
                }
                setSt(() => busy = true);
                try {
                  if (isJob) {
                    await ref.read(jobsRepositoryProvider).createJob({
                      'title': title.text.trim(), 'company': second.text.trim(),
                      'description': body.text.trim(),
                      'salary_min': salary.text.trim(), 'location': loc.text.trim(),
                    });
                  } else {
                    await ref.read(jobsRepositoryProvider).createResume({
                      'title': title.text.trim(), 'skills': second.text.trim(),
                      'about': body.text.trim(),
                      'salary_min': salary.text.trim(), 'location': loc.text.trim(),
                    });
                  }
                  if (ctx.mounted) Navigator.pop(ctx, true);
                } catch (_) {
                  setSt(() => busy = false);
                  if (ctx.mounted) {
                    ScaffoldMessenger.of(ctx).showSnackBar(
                        const SnackBar(content: Text('Yuborilmadi')));
                  }
                }
              },
              child: busy
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Joylash'),
            ),
          ],
        ),
      ),
    ),
  );
}
