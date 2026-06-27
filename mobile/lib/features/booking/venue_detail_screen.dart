import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/providers.dart';
import '../delivery/delivery_models.dart' show money;
import 'booking_models.dart';

/// Joy detali — xizmatlar, ustalar, xarita + bron qilish.
class VenueDetailScreen extends ConsumerStatefulWidget {
  const VenueDetailScreen({super.key, required this.id});
  final String id;

  @override
  ConsumerState<VenueDetailScreen> createState() => _VenueDetailScreenState();
}

class _VenueDetailScreenState extends ConsumerState<VenueDetailScreen> {
  late Future<VenueDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(bookingRepositoryProvider).detail(widget.id);
  }

  Future<void> _openMap(double lat, double lng) async {
    final uri = Uri.parse('https://maps.google.com/?q=$lat,$lng');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Joy')),
      body: FutureBuilder<VenueDetail>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return const Center(child: Text("Yuklab bo'lmadi"));
          }
          final d = snap.data!;
          final v = d.venue;
          return Column(
            children: [
              Expanded(
                child: ListView(
                  children: [
                    AspectRatio(
                      aspectRatio: 16 / 9,
                      child: v.image != null
                          ? CachedNetworkImage(imageUrl: v.image!, fit: BoxFit.cover)
                          : Container(
                              color: const Color(0xFF141B29),
                              child: const Icon(Icons.location_city, size: 56)),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(v.name,
                              style: const TextStyle(
                                  fontSize: 20, fontWeight: FontWeight.w800)),
                          const SizedBox(height: 4),
                          Text(v.venueTypeDisplay,
                              style: const TextStyle(color: Color(0xFF9AA6BD))),
                          if (v.address.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            Row(children: [
                              const Icon(Icons.place, size: 18, color: Color(0xFF9AA6BD)),
                              const SizedBox(width: 6),
                              Expanded(child: Text(v.address)),
                            ]),
                          ],
                          if (d.description.isNotEmpty) ...[
                            const SizedBox(height: 10),
                            Text(d.description, style: const TextStyle(height: 1.5)),
                          ],

                          // ── Xizmatlar ──
                          if (d.services.isNotEmpty) ...[
                            const Divider(height: 28),
                            const Text('Xizmatlar va narxlar',
                                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                            const SizedBox(height: 8),
                            ...d.services.map((s) => Padding(
                                  padding: const EdgeInsets.symmetric(vertical: 5),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Expanded(
                                        child: Text('${s.name}  ·  ${s.durationMinutes} daq',
                                            style: const TextStyle(fontSize: 14)),
                                      ),
                                      Text("${money(s.price)} so'm",
                                          style: const TextStyle(
                                              color: Color(0xFF34D399),
                                              fontWeight: FontWeight.w800)),
                                    ],
                                  ),
                                )),
                          ],

                          // ── Ustalar ──
                          if (d.staff.isNotEmpty) ...[
                            const Divider(height: 28),
                            const Text('Ustalar',
                                style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                            const SizedBox(height: 10),
                            SizedBox(
                              height: 132,
                              child: ListView.separated(
                                scrollDirection: Axis.horizontal,
                                itemCount: d.staff.length,
                                separatorBuilder: (_, __) => const SizedBox(width: 12),
                                itemBuilder: (_, i) => _staffCard(d.staff[i]),
                              ),
                            ),
                          ],

                          // ── Xarita ──
                          if (v.address.isNotEmpty && d.latitude != null && d.longitude != null) ...[
                            const Divider(height: 28),
                            OutlinedButton.icon(
                              onPressed: () => _openMap(d.latitude!, d.longitude!),
                              icon: const Icon(Icons.map),
                              label: const Text('Xaritada ko\'rish'),
                            ),
                          ],

                          if (d.prepayRequired) ...[
                            const SizedBox(height: 12),
                            Text(
                              "⚠️ Oldindan to'lov. Bekor qilinsa yoki kelinmasa ${d.penaltyPercent}% ushlanadi.",
                              style: const TextStyle(fontSize: 12, color: Color(0xFF9AA6BD)),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: EdgeInsets.fromLTRB(
                    16, 8, 16, MediaQuery.of(context).padding.bottom + 12),
                child: SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: () => context.push('/venue-book/${widget.id}'),
                    icon: const Icon(Icons.calendar_month),
                    label: const Text('Bron qilish'),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _staffCard(VenueStaff s) {
    return Container(
      width: 104,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0x22FFFFFF)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          CircleAvatar(
            radius: 26,
            backgroundColor: const Color(0xFF141B29),
            backgroundImage: s.photo != null ? CachedNetworkImageProvider(s.photo!) : null,
            child: s.photo == null
                ? Text(s.name.isNotEmpty ? s.name[0] : '?')
                : null,
          ),
          const SizedBox(height: 6),
          Text(s.name,
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
          Text('⭐ ${s.rating.toStringAsFixed(1)} (${s.reviewsCount})',
              style: const TextStyle(fontSize: 11, color: Color(0xFFCAA23A))),
          Text('${s.completedCount} ish',
              style: const TextStyle(fontSize: 10, color: Color(0xFF69748A))),
        ],
      ),
    );
  }
}
