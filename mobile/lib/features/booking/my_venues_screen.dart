import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/widgets/empty_state.dart';
import 'booking_models.dart';
import 'venue_edit_screen.dart';
import 'venue_services_screen.dart';

const _muted = Color(0xFF9AA0AC);

/// Egasi joylari ro'yxati — yangi joy qo'shish va boshqarish (setup).
class MyVenuesScreen extends ConsumerStatefulWidget {
  const MyVenuesScreen({super.key});

  @override
  ConsumerState<MyVenuesScreen> createState() => _MyVenuesScreenState();
}

class _MyVenuesScreenState extends ConsumerState<MyVenuesScreen> {
  bool _loading = true;
  String? _error;
  List<Venue> _venues = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final v = await ref.read(bookingRepositoryProvider).myVenues();
      if (mounted) setState(() { _venues = v; _loading = false; _error = null; });
    } catch (_) {
      if (mounted) setState(() { _loading = false; _error = 'Yuklab bo\'lmadi'; });
    }
  }

  Future<void> _create() async {
    final added = await Navigator.push<bool>(context,
        MaterialPageRoute(builder: (_) => const VenueEditScreen()));
    if (added == true) await _load();
  }

  Future<void> _manage(Venue v) async {
    final changed = await Navigator.push<bool>(context,
        MaterialPageRoute(builder: (_) => VenueServicesScreen(venueId: v.id)));
    if (changed == true) await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('🏛️ Joylarim')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _create,
        icon: const Icon(Icons.add),
        label: const Text('Joy qo\'shish'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : _venues.isEmpty
                  ? EmptyState(
                      icon: Icons.location_city_outlined,
                      title: 'Hali joyingiz yo\'q',
                      subtitle: "To'yxona, restoran, salon yoki sport zal qo'shing — "
                          'mijozlar bron qila boshlaydi.',
                      actionLabel: 'Joy qo\'shish',
                      onAction: _create,
                    ).scrollable()
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.all(12),
                        itemCount: _venues.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, i) {
                          final v = _venues[i];
                          return Card(
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: const Color(0xFF141B29),
                                backgroundImage:
                                    v.image != null ? NetworkImage(v.image!) : null,
                                child: v.image == null
                                    ? const Icon(Icons.location_city, color: _muted)
                                    : null,
                              ),
                              title: Text(v.name,
                                  style: const TextStyle(fontWeight: FontWeight.w700)),
                              subtitle: Text(
                                  '${v.venueTypeDisplay} · ${v.priceLabel}',
                                  style: const TextStyle(fontSize: 12)),
                              trailing: const Icon(Icons.chevron_right),
                              onTap: () => _manage(v),
                            ),
                          );
                        },
                      ),
                    ),
    );
  }
}
