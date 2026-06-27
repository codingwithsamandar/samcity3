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

  var TILE = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
  var ATTR = '© OpenStreetMap';

  // Shofirkon tumani + chegarasidan ~3km margin. Xarita shu chegaradan
  // tashqariga surilmaydi va juda uzoqlashtirib bo'lmaydi (minZoom).
  // (lat 1°≈111km, lng 1°≈85km @40°N → ±0.04 lat ≈ 4.4km, ±0.05 lng ≈ 4.2km)
  var SHOFIRKON_BOUNDS = [[40.075, 64.448], [40.156, 64.558]];

  function init(elId, opts) {
    var bounds = opts.maxBounds === null ? null : (opts.maxBounds || SHOFIRKON_BOUNDS);
    var map = L.map(elId, {
      zoomControl: opts.zoom !== false,
      scrollWheelZoom: true,
      maxBounds: bounds,
      maxBoundsViscosity: bounds ? 1.0 : 0,
      minZoom: opts.minZoom || (bounds ? 12 : undefined)
    }).setView(opts.center || CENTER, opts.zoomLevel || 13);
    L.tileLayer(TILE, { maxZoom: 19, attribution: ATTR }).addTo(map);
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
        btn.style.cssText = 'width:34px;height:34px;line-height:34px;text-align:center;background:#fff;font-size:18px;';
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
    if (p.url) html += '<a href="' + p.url + '" style="display:block;text-align:center;margin-top:.65rem;background:#0ea371;color:#fff;padding:.5rem .8rem;border-radius:9px;font-weight:700;font-size:.84rem;">To\'liq ma\'lumot →</a>';
    html += '</div>';
    m.bindPopup(html, { minWidth: 220, maxWidth: 280 });
    return m;
  }

  function driverIcon() {
    return L.divIcon({
      className: '',
      html: '<div style="background:linear-gradient(140deg,#3551d1,#2a41b8);width:36px;height:36px;border-radius:50% 50% 50% 4px;transform:rotate(45deg);display:grid;place-items:center;box-shadow:0 6px 16px rgba(0,0,0,.3);border:2px solid #fff;"><span style="transform:rotate(-45deg);font-size:18px;">🚗</span></div>',
      iconSize: [36, 36], iconAnchor: [18, 34],
    });
  }

  // ── GPS with permission handling, high accuracy + fallback ──
  function locate(opts) {
    opts = opts || {};
    return new Promise(function (resolve, reject) {
      if (!navigator.geolocation) { reject({ code: 'unsupported', message: "Brauzer geolokatsiyani qo'llamaydi" }); return; }
      var done = false;
      function ok(pos) { if (done) return; done = true; resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }); }
      function fail(err) {
        if (done) return;
        // Retry once in low-accuracy mode as a fallback.
        if (opts._retried) { done = true; reject({ code: err.code, message: gpsMsg(err) }); return; }
        opts._retried = true;
        navigator.geolocation.getCurrentPosition(ok, function (e) { done = true; reject({ code: e.code, message: gpsMsg(e) }); },
          { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 });
      }
      navigator.geolocation.getCurrentPosition(ok, fail, { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 });
    });
  }
  function gpsMsg(err) {
    if (err.code === 1) return "Joylashuvga ruxsat berilmadi";
    if (err.code === 2) return "Joylashuv aniqlanmadi";
    if (err.code === 3) return "Vaqt tugadi — qayta urinib ko'ring";
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
