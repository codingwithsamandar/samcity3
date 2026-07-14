import 'dart:math' show Point, pow;

import 'package:flutter/widgets.dart' show Color;
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:proj4dart/proj4dart.dart' as proj4;

/// Yandex xaritasi — kalitsiz raster plitka + TO'G'RI proyeksiya (EPSG:3395).
///
/// Yandex plitkalari EPSG:3395 (ellipsoidal Mercator) da. Agar ularni standart
/// EPSG:3857 xaritaga qo'ysak, ~40°N (Shofirkon) da markerlar ~21 km xato
/// bo'ladi. Shuning uchun Yandex uchun alohida CRS ishlatamiz — marker imagery
/// bilan aniq mos keladi.
///
/// Shu bilan birga xarita FAQAT Shofirkon tumani + ~10 km atrofi bilan
/// cheklanadi ([kShofirkonBounds] + [kShofirkonMinZoom]).

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

// ── Yandex EPSG:3395 CRS ─────────────────────────────────────────────────────
final proj4.Projection _yandexProjection = proj4.Projection.add(
  'EPSG:3395',
  '+proj=merc +a=6378137 +b=6356752.314245179 +lat_ts=0 +lon_0=0 '
  '+x_0=0 +y_0=0 +k=1 +units=m +nadgrids=@null +no_defs',
);

final List<double> _resolutions = [
  for (var z = 0; z <= 20; z++) 156543.033928041 / pow(2, z).toDouble(),
];

/// Yandex plitkalari uchun CRS — `MapOptions.crs` ga beriladi.
final Crs yandexCrs = Proj4Crs.fromFactory(
  code: 'EPSG:3395',
  proj4Projection: _yandexProjection,
  resolutions: _resolutions,
  origins: const [Point<double>(-20037508.342789244, 20037508.342789244)],
  bounds: Bounds<double>(
    const Point<double>(-20037508.342789244, -20037508.342789244),
    const Point<double>(20037508.342789244, 20037508.342789244),
  ),
);

/// Yandex raster plitka qatlami (kalitsiz).
TileLayer yandexTileLayer() => TileLayer(
      urlTemplate:
          'https://core-renderer-tiles.maps.yandex.net/tiles?l=map&x={x}&y={y}&z={z}&scale=1&lang=ru_RU',
      userAgentPackageName: 'uz.samcity.app',
      maxNativeZoom: 19,
      maxZoom: kShofirkonMaxZoom,
      tileProvider: NetworkTileProvider(),
    );

/// Shofirkon bilan cheklangan Yandex xarita uchun tayyor `MapOptions`.
MapOptions shofirkonMapOptions({
  LatLng? center,
  double zoom = 14,
  void Function(TapPosition, LatLng)? onTap,
}) =>
    MapOptions(
      crs: yandexCrs,
      initialCenter: center ?? kShofirkonCenter,
      initialZoom: zoom,
      minZoom: kShofirkonMinZoom,
      maxZoom: kShofirkonMaxZoom,
      // Xarita faqat Shofirkon + ~10 km atrofidan tashqariga surilmasin.
      cameraConstraint: CameraConstraint.contain(bounds: kShofirkonBounds),
      backgroundColor: const Color(0xFF0F1521),
      onTap: onTap,
    );
