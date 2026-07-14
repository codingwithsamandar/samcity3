import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

/// Buyurtma manzilini xaritada belgilash ekрani.
///
/// Foydalanuvchi ikki yo'l bilan joy tanlaydi:
///  1. Xaritaga bosib — nuqta tashlaydi.
///  2. «Mening joylashuvim» — GPS orqali hozirgi joyni oladi.
/// «Tasdiqlash» bosilganda tanlangan [LatLng] qaytariladi.
class LocationPickerScreen extends StatefulWidget {
  const LocationPickerScreen({super.key, this.initial});

  /// Oldindan tanlangan joy (tahrirlashda) — bo'lmasa Shofirkon markazi.
  final LatLng? initial;

  @override
  State<LocationPickerScreen> createState() => _LocationPickerScreenState();
}

class _LocationPickerScreenState extends State<LocationPickerScreen> {
  static const _fallbackCenter = LatLng(40.1156, 64.5036); // Shofirkon
  final _map = MapController();
  LatLng? _picked;
  bool _locating = false;

  @override
  void initState() {
    super.initState();
    _picked = widget.initial;
  }

  Future<void> _useMyLocation() async {
    setState(() => _locating = true);
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        _snack('Joylashuv (GPS) o\'chirilgan — yoqing');
        return;
      }
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied ||
          perm == LocationPermission.deniedForever) {
        _snack('Joylashuvga ruxsat berilmadi');
        return;
      }
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
      final here = LatLng(pos.latitude, pos.longitude);
      setState(() => _picked = here);
      _map.move(here, 16);
    } catch (_) {
      _snack('Joylashuvni aniqlab bo\'lmadi');
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  void _snack(String m) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final center = _picked ?? widget.initial ?? _fallbackCenter;
    return Scaffold(
      appBar: AppBar(title: const Text('Joylashuvni belgilang')),
      body: Stack(
        children: [
          FlutterMap(
            mapController: _map,
            options: MapOptions(
              initialCenter: center,
              initialZoom: _picked != null ? 16 : 14,
              onTap: (_, latLng) => setState(() => _picked = latLng),
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                // OSM ba'zi tarmoqlarda bloklanadi — Carto zaxira qatlami.
                fallbackUrl:
                    'https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
                userAgentPackageName: 'uz.samcity.app',
              ),
              if (_picked != null)
                MarkerLayer(
                  markers: [
                    Marker(
                      point: _picked!,
                      width: 44,
                      height: 44,
                      alignment: Alignment.topCenter,
                      child: const Icon(Icons.location_on,
                          color: Color(0xFFE23B3B), size: 44),
                    ),
                  ],
                ),
            ],
          ),
          // Yo'riqnoma
          Positioned(
            top: 12, left: 12, right: 12,
            child: IgnorePointer(
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xE60F1521),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Text(
                  'Xaritaga bosib joyni belgilang yoki «Mening joylashuvim» tugmasidan foydalaning.',
                  style: TextStyle(fontSize: 12, color: Colors.white),
                ),
              ),
            ),
          ),
          // «Mening joylashuvim»
          Positioned(
            right: 12,
            bottom: 92,
            child: FloatingActionButton(
              heroTag: 'myloc',
              onPressed: _locating ? null : _useMyLocation,
              child: _locating
                  ? const SizedBox(
                      width: 22, height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.my_location),
            ),
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.all(12),
        child: FilledButton.icon(
          onPressed: _picked == null
              ? null
              : () => Navigator.pop<LatLng>(context, _picked),
          icon: const Icon(Icons.check),
          label: Text(_picked == null ? 'Joyni tanlang' : 'Tasdiqlash'),
        ),
      ),
    );
  }
}
