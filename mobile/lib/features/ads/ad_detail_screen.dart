import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'ad_model.dart';

/// Bitta e'lon detali.
class AdDetailScreen extends ConsumerStatefulWidget {
  const AdDetailScreen({super.key, required this.id});
  final String id;

  @override
  ConsumerState<AdDetailScreen> createState() => _AdDetailScreenState();
}

class _AdDetailScreenState extends ConsumerState<AdDetailScreen> {
  late Future<AdDetail> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(adsRepositoryProvider).detail(widget.id);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('E\'lon')),
      body: FutureBuilder<AdDetail>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return const Center(child: Text('E\'lonni yuklab bo\'lmadi.'));
          }
          final ad = snap.data!;
          return ListView(
            children: [
              if (ad.images.isNotEmpty)
                AspectRatio(
                  aspectRatio: 16 / 10,
                  child: PageView(
                    children: ad.images
                        .map((u) => CachedNetworkImage(
                            imageUrl: u, fit: BoxFit.cover))
                        .toList(),
                  ),
                )
              else
                AspectRatio(
                  aspectRatio: 16 / 10,
                  child: Container(
                    color: const Color(0xFF141B29),
                    child: const Icon(Icons.inventory_2_outlined,
                        size: 48, color: Color(0xFF69748A)),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(ad.priceLabel,
                        style: const TextStyle(
                            fontSize: 24, fontWeight: FontWeight.w800)),
                    const SizedBox(height: 6),
                    Text(ad.title,
                        style: const TextStyle(
                            fontSize: 18, fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    Row(children: [
                      const Icon(Icons.place_outlined,
                          size: 16, color: Color(0xFF69748A)),
                      const SizedBox(width: 4),
                      Text(ad.location.isEmpty ? 'Shahar' : ad.location,
                          style: const TextStyle(color: Color(0xFF9AA6BD))),
                      const Spacer(),
                      const Icon(Icons.visibility_outlined,
                          size: 16, color: Color(0xFF69748A)),
                      const SizedBox(width: 4),
                      Text('${ad.views}',
                          style: const TextStyle(color: Color(0xFF9AA6BD))),
                    ]),
                    const Divider(height: 32),
                    if (ad.description.isNotEmpty) ...[
                      const Text('Tavsif',
                          style: TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 6),
                      Text(ad.description,
                          style: const TextStyle(height: 1.5)),
                      const SizedBox(height: 20),
                    ],
                    Row(children: [
                      CircleAvatar(
                        backgroundColor: const Color(0xFF141B29),
                        backgroundImage: ad.ownerAvatar != null
                            ? CachedNetworkImageProvider(ad.ownerAvatar!)
                            : null,
                        child: ad.ownerAvatar == null
                            ? const Icon(Icons.person)
                            : null,
                      ),
                      const SizedBox(width: 10),
                      Text(ad.ownerName,
                          style: const TextStyle(fontWeight: FontWeight.w600)),
                    ]),
                    const SizedBox(height: 20),
                    if (ad.contactPhone != null && ad.contactPhone!.isNotEmpty)
                      FilledButton.icon(
                        onPressed: () {},
                        icon: const Icon(Icons.phone),
                        label: Text(ad.contactPhone!),
                      ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
