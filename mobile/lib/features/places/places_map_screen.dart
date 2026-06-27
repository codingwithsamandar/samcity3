import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../core/providers.dart';
import 'place_model.dart';

/// Interaktiv xarita — joylar (OpenStreetMap). Saytdagi Leaflet bilan bir xil.
class PlacesMapScreen extends ConsumerStatefulWidget {
  const PlacesMapScreen({super.key});

  @override
  ConsumerState<PlacesMapScreen> createState() => _PlacesMapScreenState();
}

class _PlacesMapScreenState extends ConsumerState<PlacesMapScreen> {
  static final _center = LatLng(40.1156, 64.5036); // Shofirkon
  final _mapController = MapController();
  Future<PlacesData>? _future;
  String _cat = '';

  @override
  void initState() {
    super.initState();
    _future = ref.read(placesRepositoryProvider).places();
  }

  void _reload() {
    setState(() {
      _future = ref.read(placesRepositoryProvider)
          .places(category: _cat.isEmpty ? null : _cat);
    });
  }

  Color _color(String hex) {
    try {
      var h = hex.replaceAll('#', '');
      if (h.length == 6) h = 'FF$h';
      return Color(int.parse(h, radix: 16));
    } catch (_) {
      return const Color(0xFF0EA371);
    }
  }

  void _showPlace(Place p) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF0F1521),
      isScrollControlled: true,
      builder: (_) => Padding(
        padding: EdgeInsets.only(
          left: 16, right: 16, top: 16,
          bottom: MediaQuery.of(context).viewInsets.bottom + 20,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (p.image != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: CachedNetworkImage(
                    imageUrl: p.image!, height: 140, width: double.infinity,
                    fit: BoxFit.cover),
              ),
            const SizedBox(height: 10),
            Text('${p.icon} ${p.name}',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            Text(p.categoryLabel,
                style: TextStyle(color: _color(p.color), fontWeight: FontWeight.w700, fontSize: 12)),
            if (p.description.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(p.description, style: const TextStyle(color: Color(0xFF9AA6BD), height: 1.5)),
            ],
            const SizedBox(height: 8),
            if (p.address.isNotEmpty) _row(Icons.place, p.address),
            if (p.phone.isNotEmpty) _row(Icons.phone, p.phone),
            if (p.hours.isNotEmpty) _row(Icons.schedule, p.hours),
          ],
        ),
      ),
    );
  }

  Widget _row(IconData ic, String t) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [
          Icon(ic, size: 16, color: const Color(0xFF69748A)),
          const SizedBox(width: 8),
          Expanded(child: Text(t)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Xarita')),
      body: FutureBuilder<PlacesData>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return const Center(child: Text("Xaritani yuklab bo'lmadi"));
          }
          final data = snap.data!;
          return Column(
            children: [
              // Toifa filtri
              SizedBox(
                height: 48,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                  children: [
                    _chip('Barchasi', ''),
                    ...data.categories.map((c) => _chip(c.label, c.key)),
                  ],
                ),
              ),
              Expanded(
                child: FlutterMap(
                  mapController: _mapController,
                  options: MapOptions(initialCenter: _center, initialZoom: 13),
                  children: [
                    TileLayer(
                      urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: 'uz.samcity.app',
                    ),
                    MarkerLayer(
                      markers: data.places.where((p) => p.lat != 0).map((p) {
                        return Marker(
                          point: LatLng(p.lat, p.lng),
                          width: 40, height: 40,
                          child: GestureDetector(
                            onTap: () => _showPlace(p),
                            child: Icon(Icons.location_on,
                                color: _color(p.color), size: 36),
                          ),
                        );
                      }).toList(),
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

  Widget _chip(String label, String key) {
    final sel = _cat == key;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: ChoiceChip(
        label: Text(label),
        selected: sel,
        onSelected: (_) {
          _cat = key;
          _reload();
        },
      ),
    );
  }
}
