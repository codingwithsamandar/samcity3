import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import 'booking_models.dart';

const _venueTypes = <String, String>{
  '': 'Barchasi',
  'wedding': "To'yxona",
  'restaurant': 'Restoran',
  'cafe': 'Kafe',
  'barber': 'Sartaroshxona',
  'beauty': "Go'zallik",
  'gym': 'Sport zal',
  'other': 'Boshqa',
};

/// Joylar (venue) ro'yxati + tur bo'yicha filtr.
class VenuesScreen extends ConsumerStatefulWidget {
  const VenuesScreen({super.key});

  @override
  ConsumerState<VenuesScreen> createState() => _VenuesScreenState();
}

class _VenuesScreenState extends ConsumerState<VenuesScreen> {
  String _type = '';
  late Future<List<Venue>> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(bookingRepositoryProvider).venues();
  }

  void _select(String type) {
    setState(() {
      _type = type;
      _future = ref.read(bookingRepositoryProvider).venues(type: type);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Joylar'),
        actions: [
          IconButton(
            tooltip: 'Bronlarim',
            onPressed: () => context.push('/my-bookings'),
            icon: const Icon(Icons.event_note),
          ),
        ],
      ),
      body: Column(
        children: [
          SizedBox(
            height: 52,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              children: _venueTypes.entries.map((e) {
                final sel = _type == e.key;
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(e.value),
                    selected: sel,
                    onSelected: (_) => _select(e.key),
                  ),
                );
              }).toList(),
            ),
          ),
          Expanded(
            child: FutureBuilder<List<Venue>>(
              future: _future,
              builder: (context, snap) {
                if (snap.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snap.hasError) {
                  return const Center(child: Text("Joylarni yuklab bo'lmadi"));
                }
                final venues = snap.data ?? [];
                if (venues.isEmpty) {
                  return const Center(child: Text("Joylar topilmadi"));
                }
                return ListView.separated(
                  padding: const EdgeInsets.all(12),
                  itemCount: venues.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (_, i) => _VenueCard(venue: venues[i]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _VenueCard extends StatelessWidget {
  const _VenueCard({required this.venue});
  final Venue venue;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => context.push('/venue/${venue.id}'),
      borderRadius: BorderRadius.circular(16),
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AspectRatio(
              aspectRatio: 16 / 8,
              child: venue.image != null
                  ? CachedNetworkImage(imageUrl: venue.image!, fit: BoxFit.cover)
                  : Container(
                      color: const Color(0xFF141B29),
                      child: const Icon(Icons.location_city,
                          size: 40, color: Color(0xFF69748A)),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(venue.name,
                            style: const TextStyle(
                                fontWeight: FontWeight.w800, fontSize: 16)),
                      ),
                      Chip(
                        label: Text(venue.venueTypeDisplay,
                            style: const TextStyle(fontSize: 11)),
                        padding: EdgeInsets.zero,
                        visualDensity: VisualDensity.compact,
                      ),
                    ],
                  ),
                  if (venue.address.isNotEmpty)
                    Text(venue.address,
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Color(0xFF9AA6BD))),
                  const SizedBox(height: 4),
                  Text(venue.priceLabel,
                      style: const TextStyle(
                          color: Color(0xFF34D399), fontWeight: FontWeight.w700)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
