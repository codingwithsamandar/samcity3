/* ============================================================
   SamCity — shared map engine (Leaflet + OpenStreetMap)
   Single source of truth for map init, markers, clustering,
   GPS, routing and reverse-geocoding. Reused by every map page.
   Config is injected per-page via window.SAMMAP (URLs + center).
   ============================================================ */
(function (global) {
  'use strict';
  var CFG = global.SAMMAP || {};
  var CENTER = CFG.center || [40.1156, 64.5036];

  var COLORS = {
    furniture: '#b45309', electronics: '#2563eb', tourist: '#9333ea',
    government: '#475569', organization: '#0891b2', post: '#ea580c',
    bank: '#15803d', pharmacy: '#dc2626', hospital: '#e11d48',
    hotel: '#7c3aed', wedding: '#db2777', restaurant: '#d97706',
    delivery_store: '#059669',
    // community layers
    help: '#3551d1', emergency: '#e5484d', event: '#7a5af8', driver: '#e0a52e',
  };

  // ── Plitka manbalari ─────────────────────────────────────────────────
  // Manba serverdan keladi (settings.MAP_TILE_PROVIDER), default — 'yandex'.
  //
  // LITSENZIYA OGOHLANTIRISHI: 'yandex' varianti Yandex plitkalarini
  // to'g'ridan-to'g'ri chaqiradi. Bu ularning foydalanish shartlariga zid —
  // istalgan payt bloklanishi yoki huquqiy talab kelib chiqishi mumkin.
  // U ataylab tanlangan, chunki O'zbekistonda OpenStreetMap ma'lumoti kam
  // (Shofirkon markazi, z16: Yandex 12.4% detal, OSM asosidagilar 3.2%).
  // Litsenziyali variantga o'tish uchun .env da bitta qator yetarli:
  //   MAP_TILE_PROVIDER=maptiler + MAP_TILE_KEY=<kalit>
  //
  // Har provayder:
  //   base       — asos qatlam
  //   baseMax    — shu zoomgacha base; undan keyin sat (0 = almashinuv yo'q)
  //   sat        — yaqinlashtirilganda ishlatiladigan sputnik (ixtiyoriy)
  //   labels     — base ustidagi yozuv qatlami (ixtiyoriy)
  //   crs3395    — Yandex proyeksiyasi (proj4leaflet kerak)
  var PROVIDERS = {
    // Avvalgi (asl) ko'rinish: z<=15 chizma — ko'cha/mahalla nomlari bilan,
    // z>=16 sputnik — chizma bu yerdan uy raqamlarini chizgani uchun.
    yandex: {
      base: 'https://core-renderer-tiles.maps.yandex.net/tiles?l=map&x={x}&y={y}&z={z}&scale=1&lang=ru_RU',
      // Sputnik qatlami YO'Q: ilgari z16 dan sputnik tasviriga o'tilardi
      // (chizma u yerdan uy raqamlarini chizgani uchun), ammo natijada
      // xarita yaqinlashtirilganda uy tomlari suratiga aylanib qolardi.
      // Endi barcha masshtablarda chizma — ko'cha va yo'llar chiziq bo'lib
      // ko'rinadi. Evazi: z16+ da uy raqamlari chiqadi.
      baseMax: 0, maxNative: 19,
      crs3395: true,
      attr: '&copy; Yandex',
    },
    // Kalitsiz, ODbL. Ko'cha nomlari bor, ammo bino ma'lumoti kam.
    osm: {
      base: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      baseMax: 0, maxNative: 19,
      attr: '&copy; OpenStreetMap hissadorlari',
    },
    // Kalit bilan. Sputnik + ko'cha nomlari ustma-ust.
    maptiler: {
      base: 'https://api.maptiler.com/tiles/satellite-v2/{z}/{x}/{y}.jpg?key={key}',
      labels: 'https://api.maptiler.com/maps/hybrid/{z}/{x}/{y}.png?key={key}',
      baseMax: 0, maxNative: 20,
      attr: '&copy; MapTiler &copy; OpenStreetMap hissadorlari',
    },
    // Kalit bilan. satellite-streets: sputnik + yo'l/nomlar bitta uslubda.
    mapbox: {
      base: 'https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v12/tiles/{z}/{x}/{y}?access_token={key}',
      baseMax: 0, maxNative: 20,
      attr: '&copy; Mapbox &copy; OpenStreetMap hissadorlari',
    },
  };

  var PROVIDER = PROVIDERS[CFG.tileProvider] || PROVIDERS.yandex;
  var TILE_KEY = CFG.tileKey || '';
  var MAX_ZOOM = 21;

  function tileUrl(tpl) {
    return tpl ? tpl.replace('{key}', encodeURIComponent(TILE_KEY)) : null;
  }

  // Yandex EPSG:3395 CRS — bir marta yaratib keshlaymiz (proj4leaflet kerak).
  // CRS'siz Yandex plitkalarida markerlar ~21km siljib ketadi.
  var _yandexCRS = null;
  function yandexCRS() {
    if (_yandexCRS) return _yandexCRS;
    if (!L.Proj) return null; // proj4leaflet yuklanmagan — standart CRS
    var res = [];
    for (var z = 0; z <= MAX_ZOOM; z++) res.push(156543.033928041 / Math.pow(2, z));
    _yandexCRS = new L.Proj.CRS('EPSG:3395',
      '+proj=merc +a=6378137 +b=6356752.314245179 +lat_ts=0 +lon_0=0 ' +
      '+x_0=0 +y_0=0 +k=1 +units=m +nadgrids=@null +no_defs',
      {
        origin: [-20037508.342789244, 20037508.342789244],
        resolutions: res,
        bounds: L.bounds([-20037508.342789244, -20037508.342789244],
                         [20037508.342789244, 20037508.342789244])
      });
    return _yandexCRS;
  }

  // Shofirkon tumani + ~10km atrofi. Xarita shu chegaradan tashqariga surilmaydi
  // va juda uzoqlashtirib bo'lmaydi (minZoom). (10km ≈ 0.09° lat, 0.117° lng @40°N)
  var SHOFIRKON_BOUNDS = [[39.985, 64.331], [40.246, 64.676]];


  function init(elId, opts) {
    var bounds = opts.maxBounds === null ? null : (opts.maxBounds || SHOFIRKON_BOUNDS);
    var mapOpts = {
      zoomControl: opts.zoom !== false,
      scrollWheelZoom: true,
      maxBounds: bounds,
      maxBoundsViscosity: bounds ? 1.0 : 0,
      minZoom: opts.minZoom || (bounds ? 11 : undefined),
      maxZoom: MAX_ZOOM
    };
    // Yandex plitkalari EPSG:3395 da; qolgan manbalar standart EPSG:3857 da.
    if (PROVIDER.crs3395) {
      var crs = yandexCRS();
      if (crs) mapOpts.crs = crs;
    }
    var map = L.map(elId, mapOpts).setView(opts.center || CENTER, opts.zoomLevel || 11);

    // Asos qatlam. baseMax > 0 bo'lsa — shu zoomdan keyin sputnikka o'tadi
    // (Yandex chizmasi z16 dan uy raqamlarini chizgani uchun shunday).
    L.tileLayer(tileUrl(PROVIDER.base), {
      maxZoom: PROVIDER.baseMax || MAX_ZOOM,
      maxNativeZoom: PROVIDER.maxNative,
      attribution: PROVIDER.attr
    }).addTo(map);

    if (PROVIDER.sat) {
      L.tileLayer(tileUrl(PROVIDER.sat), {
        minZoom: (PROVIDER.baseMax || 0) + 1,
        maxNativeZoom: PROVIDER.satMaxNative, maxZoom: MAX_ZOOM,
        attribution: PROVIDER.attr
      }).addTo(map);
    }

    // Ko'cha nomlari asos ustida (provayderda alohida qatlam bo'lsa).
    if (PROVIDER.labels) {
      L.tileLayer(tileUrl(PROVIDER.labels), {
        maxZoom: MAX_ZOOM, maxNativeZoom: PROVIDER.maxNative
      }).addTo(map);
    }

    if (opts.fullscreen !== false) addFullscreen(map, elId);
    // Tile/layout race: recalc size after the container settles.
    setTimeout(function () { map.invalidateSize(); }, 400);
    return map;
  }

  function addFullscreen(map, elId) {
    var Ctrl = L.Control.extend({
      options: { position: 'topright' },
      onAdd: function () {
        var btn = L.DomUtil.create('a', 'leaflet-bar');
        btn.href = '#'; btn.title = "To'liq ekran";
        // Fon/rang CSS'da (sahifa mavzusiga mos). Ilgari bu yerda inline
        // 'background:#fff' bor edi — inline uslub CSS'ni bosib, tugma
        // qorong'i xarita ustida oq quti bo'lib turardi.
        btn.className = 'leaflet-bar sam-fs-btn';
        btn.innerHTML = '⤢';
        L.DomEvent.on(btn, 'click', function (e) {
          L.DomEvent.preventDefault(e);
          var el = document.getElementById(elId);
          if (!document.fullscreenElement) { (el.requestFullscreen || el.webkitRequestFullscreen || function(){}).call(el); }
          else { (document.exitFullscreen || document.webkitExitFullscreen || function(){}).call(document); }
          setTimeout(function () { map.invalidateSize(); }, 300);
        });
        return btn;
      }
    });
    map.addControl(new Ctrl());
  }

  function cluster(map) {
    var layer = (typeof L.markerClusterGroup === 'function') ? L.markerClusterGroup({ maxClusterRadius: 50 }) : L.layerGroup();
    map.addLayer(layer);
    return layer;
  }

  function colorFor(cat) { return COLORS[cat] || '#3551d1'; }

  function placeMarker(p) {
    var m = L.circleMarker([p.lat, p.lng], {
      radius: p.radius || 9, color: '#fff', weight: 2.5,
      fillColor: p.color || colorFor(p.category), fillOpacity: 0.98,
    });
    var html = '<div style="min-width:210px;max-width:260px;">';
    // Rasm (mavjud bo'lsa) — yuqorida
    if (p.image) html += '<img src="' + p.image + '" alt="" style="width:100%;height:118px;object-fit:cover;border-radius:10px;margin-bottom:.55rem;display:block;" onerror="this.style.display=\'none\'">';
    html += '<div style="font-weight:800;font-family:sans-serif;font-size:.98rem;">' + (p.icon || '') + ' ' + esc(p.name || '') + '</div>';
    if (p.cat) html += '<div style="color:#0ea371;font-size:.72rem;font-weight:700;text-transform:uppercase;margin:.25rem 0;">' + esc(p.cat) + '</div>';
    if (p.desc) html += '<div style="font-size:.82rem;color:#5b6678;margin:.3rem 0;line-height:1.45;">' + esc(p.desc) + '</div>';
    if (p.address) html += '<div style="font-size:.82rem;color:#5b6678;margin-top:.2rem;">📍 ' + esc(p.address) + '</div>';
    if (p.phone) html += '<div style="font-size:.82rem;color:#5b6678;">📞 ' + esc(p.phone) + '</div>';
    if (p.hours) html += '<div style="font-size:.82rem;color:#5b6678;">🕒 ' + esc(p.hours) + '</div>';
    if (p.has_menu) html += '<div style="font-size:.82rem;color:#0ea371;font-weight:700;margin-top:.3rem;">🍽️ Menyu bor</div>';
    if (p.url) {
      // Bron joylari (booking.Venue) uchun tugma — "Bron qilish".
      var _btn = p.book ? 'Bron qilish →'
        : (p.has_menu ? 'Menyu va ma\'lumot →' : 'To\'liq ma\'lumot →');
      html += '<a href="' + p.url + '" style="display:block;text-align:center;margin-top:.65rem;background:#0ea371;color:#fff;padding:.5rem .8rem;border-radius:9px;font-weight:700;font-size:.84rem;">' + _btn + '</a>';
    }
    html += '</div>';
    // maxHeight: mobil xaritada balandlik cheklangan (55vh); rasm+matn+tugma
    // konteynerdan oshib ketsa, Leaflet uni overflow:hidden bilan yuqoridan
    // (sarlavha, rasm) kesib tashlaydi. maxHeight ichki scroll yoqadi —
    // sarlavha har doim yuqorida, ko'rinadigan bo'lib qoladi.
    m.bindPopup(html, { minWidth: 220, maxWidth: 280, maxHeight: 260 });
    return m;
  }

  function driverIcon() {
    return L.divIcon({
      className: '',
      html: '<div style="background:linear-gradient(140deg,#3551d1,#2a41b8);width:36px;height:36px;border-radius:50% 50% 50% 4px;transform:rotate(45deg);display:grid;place-items:center;box-shadow:0 6px 16px rgba(0,0,0,.3);border:2px solid #fff;"><span style="transform:rotate(-45deg);font-size:18px;">🚗</span></div>',
      iconSize: [36, 36], iconAnchor: [18, 34],
    });
  }

  // ── GPS ──
  // getCurrentPosition birinchi kelgan fiksni qaytaradi — bu odatda Wi-Fi/uyali
  // tarmoq bo'yicha taxminiy nuqta (aniqligi 1-20 km, ko'pincha shahar markazi).
  // Haqiqiy GPS fiksi 5-20 soniyada keladi va aniqligi o'nlab metr. Shuning uchun
  // watchPosition bilan fikslarni kuzatamiz va eng aniqini tanlaymiz:
  //   • aniqlik desiredAccuracy dan yaxshi bo'lsa — darhol qaytaramiz
  //   • maxWait tugasa — shu paytgacha kelgan eng aniq fiksni qaytaramiz
  // Tarmoq fiksining e'lon qilgan "accuracy" si O'zbekistonda ishonchsiz va
  // baribir yaroqsiz: telefonda baza stansiyasi bo'yicha nuqta Peshku tumaniga —
  // 18 km narida — tushdi (2000 m aniqlik da'vo qilgan holda), kompyuterda esa
  // Wi-Fi/IP bo'yicha aniqlik 50 km (butun tumandan katta). Shuning uchun
  // maxAccuracy qat'iy — bunday nuqta "joylashuvingiz" deb ko'rsatilmaydi.
  // Kompyuterda GPS qurilmasi yo'q: u yerda yagona to'g'ri yo'l — xaritadan
  // qo'lda tanlash, shuning uchun xato xabari aynan shunga yo'naltiradi.
  // opts: { desiredAccuracy (m, default 50), maxWait (ms, default 20000),
  //         maxAccuracy (m, default 300 — bundan qo'poli "aniq" emas),
  //         onProgress(fix) }
  // Uyali baza stansiyasi fiksi eng yomoni ~2-5 km (sinovda 2000 m). Bundan
  // o'n barobar qo'poli — IP bo'yicha taxmin, ya'ni qurilmada joylashuv
  // apparati umuman yo'q (kompyuterda 50 km kuzatildi). Bunday fiks kutish
  // bilan hech qachon yaxshilanmaydi — darhol to'xtaymiz.
  var IP_LEVEL = 20000;

  function locate(opts) {
    opts = opts || {};
    var desired = opts.desiredAccuracy || 50;
    var maxWait = opts.maxWait || 20000;
    var maxAcc = opts.maxAccuracy || 300;
    return new Promise(function (resolve, reject) {
      if (!navigator.geolocation) { reject({ code: 'unsupported', message: "Brauzer geolokatsiyani qo'llamaydi" }); return; }
      var done = false, watchId = null, timer = null, best = null, lastErr = null, coarse = null;

      function stop() {
        if (watchId !== null) { navigator.geolocation.clearWatch(watchId); watchId = null; }
        if (timer) { clearTimeout(timer); timer = null; }
      }
      function finish() {
        if (done) return; done = true; stop();
        if (best) { resolve(best); return; }
        if (lastErr && lastErr.code === 1) { reject({ code: 1, message: gpsMsg(lastErr) }); return; }
        // Faqat tarmoq fiksi keldi — uni ko'rsatish xato (18 km gacha adashadi).
        // Sababini aytamiz, aks holda "vaqt tugadi" chalg'ituvchi bo'ladi.
        if (coarse) {
          var acc = coarse >= 1000 ? Math.round(coarse / 1000) + ' km' : Math.round(coarse) + ' m';
          // O'nlab km aniqlik — bu Wi-Fi/IP darajasidagi taxmin, ya'ni qurilmada
          // GPS qabul qilgichi yo'q (odatda kompyuter). U yerda "ochiq havoga
          // chiqing" bema'ni maslahat: fiks kutish bilan yaxshilanmaydi, shuning
          // uchun yagona ishlaydigan yo'l — qo'lda tanlashga yo'naltiramiz.
          reject({
            code: 'coarse',
            accuracy: coarse,
            message: coarse >= IP_LEVEL
              ? "Bu qurilmada GPS yo'q — joylashuv internet orqali faqat ~" + acc +
                " aniqlikda taxmin qilindi. Joyni xaritadan qo'lda belgilang."
              : "Faqat taxminiy joylashuv topildi (~" + acc +
                " xatolik) — GPS'ni yoqing, ochiq havoga chiqing yoki xaritadan qo'lda tanlang",
          });
          return;
        }
        if (lastErr) { reject({ code: lastErr.code, message: gpsMsg(lastErr) }); return; }
        reject({ code: 3, message: gpsMsg({ code: 3 }) });
      }
      function ok(pos) {
        if (done) return;
        var acc = pos.coords.accuracy;
        // Aniqligi ma'lum bo'lmagan yoki qo'pol (tarmoq darajasidagi) fiks — hozircha
        // kutamiz, GPS yaxshirog'ini berishi mumkin; bermasa sababini aytamiz.
        if (typeof acc !== 'number' || acc > maxAcc) {
          if (typeof acc === 'number' && (coarse === null || acc < coarse)) coarse = acc;
          // IP darajasidagi fiks — GPS keyin ham kelmaydi, 20 soniya behuda
          // ushlab turmasdan darhol sababini aytamiz.
          if (coarse !== null && coarse >= IP_LEVEL) finish();
          return;
        }
        if (!best || acc < best.accuracy) {
          best = { lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: acc };
          if (typeof opts.onProgress === 'function') { try { opts.onProgress(best); } catch (e) {} }
        }
        if (best.accuracy <= desired) finish();
      }
      function fail(err) {
        if (done) return;
        lastErr = err;
        // Ruxsat berilmadi — kutishdan foyda yo'q.
        if (err.code === 1) finish();
      }

      watchId = navigator.geolocation.watchPosition(ok, fail,
        { enableHighAccuracy: true, timeout: maxWait, maximumAge: 0 });
      timer = setTimeout(finish, maxWait);
    });
  }
  // GPS'siz qurilmada "qayta urinib ko'ring" behuda maslahat — har bir chaqiruvchi
  // sahifada xarita bor, shuning uchun ishlaydigan yo'lni ham aytamiz.
  function gpsMsg(err) {
    if (err.code === 1) return "Joylashuvga ruxsat berilmadi";
    if (err.code === 2) return "Joylashuv aniqlanmadi — joyni xaritadan qo'lda belgilang";
    if (err.code === 3) return "GPS signali topilmadi — qayta urinib ko'ring yoki joyni xaritadan qo'lda belgilang";
    return "Joylashuvni aniqlab bo'lmadi";
  }

  // ── Reverse geocoding (server proxy) ──
  function reverseGeocode(lat, lng) {
    if (!CFG.revGeoUrl) return Promise.resolve('');
    return fetch(CFG.revGeoUrl + '?lat=' + lat + '&lng=' + lng).then(function (r) { return r.json(); })
      .then(function (d) { return d.address || ''; }).catch(function () { return ''; });
  }

  // ── Routing (server proxy → OSRM) ──
  function route(from, to, profile) {
    if (!CFG.routeUrl) return Promise.reject('no_route_url');
    var u = CFG.routeUrl + '?from=' + from[0] + ',' + from[1] + '&to=' + to[0] + ',' + to[1] + '&profile=' + (profile || 'driving');
    return fetch(u).then(function (r) { return r.json(); });
  }
  function drawRoute(map, geometry, existing) {
    if (existing) { existing.setLatLngs(geometry); return existing; }
    return L.polyline(geometry, { color: '#3551d1', weight: 5, opacity: 0.8, lineCap: 'round' }).addTo(map);
  }

  function haversine(a, b) {
    var R = 6371, rad = function (d) { return d * Math.PI / 180; };
    var dLat = rad(b[0] - a[0]), dLng = rad(b[1] - a[1]);
    var s = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[0])) * Math.cos(rad(b[0])) * Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
  }

  function esc(s) { return (s || '').toString().replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  global.SamMap = {
    CENTER: CENTER, COLORS: COLORS, init: init, cluster: cluster, colorFor: colorFor,
    placeMarker: placeMarker, driverIcon: driverIcon, locate: locate,
    reverseGeocode: reverseGeocode, route: route, drawRoute: drawRoute, haversine: haversine, esc: esc,
  };
})(window);
