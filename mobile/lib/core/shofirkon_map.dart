import 'dart:math' show Point, pow;

import 'package:flutter/widgets.dart' show Color, Widget;
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:proj4dart/proj4dart.dart' as proj4;

/// Xarita asosi — uy raqamlarisiz, lekin boy Yandex plitkasi.
///
/// Yandex chizma qatlami uy raqamlarini aynan **z16 dan** chiza boshlaydi; z15 va
/// undan uzoqda esa faqat ko'cha/mahalla nomlari va do'kon-maktab kabi joylar
/// bo'ladi. Sputnik qatlamida esa umuman yozuv yo'q. Shu sabab masshtabga qarab
/// ikki qatlam almashadi ([basemapLayers]):
///   z<=15 chizma  — nomlar bor, raqam yo'q
///   z>=16 sputnik — raqam yo'q, z21 gacha yaqinlashadi (z19 dan keyin cho'ziladi)
///
/// KRITIK — proyeksiya: Yandex plitkalari EPSG:3395 (ellipsoidal Mercator) da.
/// Standart EPSG:3857 ga qo'yilsa ~40°N (Shofirkon) da markerlar ~21 km xato
/// bo'ladi, shuning uchun [yandexCrs] ishlatiladi.
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
const double kShofirkonMaxZoom = 21;

/// Chizma qatlami shu masshtabgacha — bundan yuqorida uy raqamlari chiqadi.
const double _kSchemeMaxZoom = 15;

/// Sputnikning eng chuqur haqiqiy plitkasi (undan keyin tasvir cho'ziladi).
const int _kSatMaxNative = 19;

// ── Yandex EPSG:3395 CRS ─────────────────────────────────────────────────────
final proj4.Projection _yandexProjection = proj4.Projection.add(
  'EPSG:3395',
  '+proj=merc +a=6378137 +b=6356752.314245179 +lat_ts=0 +lon_0=0 '
  '+x_0=0 +y_0=0 +k=1 +units=m +nadgrids=@null +no_defs',
);

final List<double> _resolutions = [
  for (var z = 0; z <= kShofirkonMaxZoom.toInt(); z++)
    156543.033928041 / pow(2, z).toDouble(),
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

/// Xarita asosi — pastda chizma (z<=15), tepada sputnik (z>=16).
///
/// `FlutterMap.children` ning BOSHIGA qo'yiladi (markerlar ustidan tushmasin).
/// Qatlam darajasidagi minZoom/maxZoom tufayli raqamli chizma z16+ da umuman
/// yuklanmaydi.
List<Widget> basemapLayers() => [
      TileLayer(
        urlTemplate:
            'https://core-renderer-tiles.maps.yandex.net/tiles?l=map&x={x}&y={y}&z={z}&scale=1&lang=ru_RU',
        userAgentPackageName: 'uz.samcity.app',
        maxNativeZoom: _kSchemeMaxZoom.toInt(),
        maxZoom: _kSchemeMaxZoom,
        tileProvider: NetworkTileProvider(),
      ),
      TileLayer(
        urlTemplate:
            'https://core-sat.maps.yandex.net/tiles?l=sat&v=3.1000.0&x={x}&y={y}&z={z}',
        userAgentPackageName: 'uz.samcity.app',
        minZoom: _kSchemeMaxZoom + 1,
        maxNativeZoom: _kSatMaxNative,
        maxZoom: kShofirkonMaxZoom,
        tileProvider: NetworkTileProvider(),
      ),
    ];

/// Shofirkon bilan cheklangan xarita uchun tayyor `MapOptions`.
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
