import 'package:flutter/widgets.dart' show Color;
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

/// Xarita asosi — yorliqsiz (no-labels) raster plitka.
///
/// Carto Positron "light_nolabels": uy raqamlari va ko'cha nomlari
/// ko'rsatilmaydi, faqat bizning markerlarimiz ko'rinadi. Plitka standart
/// EPSG:3857 da — flutter_map default CRS'i bilan mos, shuning uchun alohida
/// proyeksiya (ilgari Yandex EPSG:3395 uchun kerak bo'lgan) ishlatilmaydi.
///
/// Xarita FAQAT Shofirkon tumani + ~10 km atrofi bilan cheklanadi
/// ([kShofirkonBounds] + [kShofirkonMinZoom]).

/// Shofirkon markazi.
const LatLng kShofirkonCenter = LatLng(40.1156, 64.5036);

/// Xarita ko'rinadigan chegara — Shofirkon tumani + ~10 km atrof.
/// (10 km ≈ 0.09° kenglik, 0.117° uzunlik @40°N)
final LatLngBounds kShofirkonBounds = LatLngBounds(
  const LatLng(39.985, 64.331), // SW
  const LatLng(40.246, 64.676), // NE
);

/// Bundan uzoqlashtirib bo'lmaydi (butun dunyo ko'rinib ketmasin).
const double kShofirkonMinZoom = 11;
const double kShofirkonMaxZoom = 19;

/// Yorliqsiz raster plitka qatlami.
TileLayer basemapTileLayer() => TileLayer(
      urlTemplate:
          'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png',
      subdomains: const ['a', 'b', 'c', 'd'],
      userAgentPackageName: 'uz.samcity.app',
      maxNativeZoom: 19,
      maxZoom: kShofirkonMaxZoom,
      tileProvider: NetworkTileProvider(),
    );

/// Shofirkon bilan cheklangan xarita uchun tayyor `MapOptions`.
MapOptions shofirkonMapOptions({
  LatLng? center,
  double zoom = 14,
  void Function(TapPosition, LatLng)? onTap,
}) =>
    MapOptions(
      initialCenter: center ?? kShofirkonCenter,
      initialZoom: zoom,
      minZoom: kShofirkonMinZoom,
      maxZoom: kShofirkonMaxZoom,
      // Xarita faqat Shofirkon + ~10 km atrofidan tashqariga surilmasin.
      cameraConstraint: CameraConstraint.contain(bounds: kShofirkonBounds),
      backgroundColor: const Color(0xFF0F1521),
      onTap: onTap,
    );
