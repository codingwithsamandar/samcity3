/* Mahalla chegarasini admin'da faqat ODDIY Leaflet bilan chizish/tahrirlash.
   Leaflet.draw plagini kerak emas (u CDN'da ko'pincha yuklanmaydi) — nuqtalar
   divIcon bilan chiziladi, rasm ham kerak emas.

   - Xaritaga bosib nuqta qo'shiladi (kamida 3 ta nuqta = poligon).
   - Nuqtani tortib joyini o'zgartirish mumkin.
   - Nuqta ustiga ikki marta bosilsa — o'chadi.
   - "Oxirgi" / "Tozalash" tugmalari.
   #id_boundary maydoni JSON [[lat,lng],...] bilan, Markaz (center_lat/center_lng)
   esa centroid bilan avtomatik sinxronlanadi. */
(function () {
  function round6(n) { return Math.round(n * 1e6) / 1e6; }
  function centroid(lls) {
    var n = lls.length;
    if (!n) return null;
    var la = 0, ln = 0;
    lls.forEach(function (p) { la += p.lat; ln += p.lng; });
    return [round6(la / n), round6(ln / n)];
  }

  function init() {
    var ta = document.getElementById('id_boundary');
    var mapDiv = document.getElementById('mahallaEditorMap');
    if (!ta || !mapDiv || typeof L === 'undefined') return;

    var DEFAULT = [40.1156, 64.5036]; // Shofirkon markazi
    var saved = [];
    try { saved = JSON.parse(ta.value || '[]') || []; } catch (e) { saved = []; }

    var start = DEFAULT;
    if (saved.length) {
      start = [saved.reduce(function (s, p) { return s + p[0]; }, 0) / saved.length,
               saved.reduce(function (s, p) { return s + p[1]; }, 0) / saved.length];
    }
    var map = L.map('mahallaEditorMap').setView(start, saved.length ? 15 : 14);

    // OSM asosiy qatlam; bloklansa Carto zaxirasiga o'tamiz.
    var osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '© OpenStreetMap'
    });
    var carto = L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
      { maxZoom: 20, subdomains: 'abcd', attribution: '© OpenStreetMap, © CARTO' }
    );
    var switched = false;
    osm.on('tileerror', function () {
      if (switched) return;
      switched = true;
      try { map.removeLayer(osm); } catch (e) {}
      carto.addTo(map);
    });
    osm.addTo(map);

    var vertices = [];   // L.marker ro'yxati (poligon tugunlari)
    var poly = L.polygon([], { color: '#3551d1', weight: 2, fillOpacity: 0.15 }).addTo(map);

    function vIcon() {
      return L.divIcon({ className: 'mh-vertex', html: '', iconSize: [14, 14], iconAnchor: [7, 7] });
    }
    function redraw() {
      poly.setLatLngs(vertices.map(function (m) { return m.getLatLng(); }));
    }
    function updateCount() {
      var el = document.querySelector('.mh-editor-ctl .mh-count');
      if (el) el.textContent = vertices.length ? (vertices.length + ' nuqta') : '';
    }
    function sync() {
      var arr = vertices.map(function (m) {
        var ll = m.getLatLng();
        return [round6(ll.lat), round6(ll.lng)];
      });
      ta.value = arr.length ? JSON.stringify(arr) : '';
      var cl = document.getElementById('id_center_lat');
      var cn = document.getElementById('id_center_lng');
      if (cl && cn) {
        var c = centroid(vertices.map(function (m) { return m.getLatLng(); }));
        if (c) { cl.value = c[0]; cn.value = c[1]; }
      }
      updateCount();
    }
    function bindVertex(m) {
      m.on('drag', redraw);
      m.on('dragend', sync);
      m.on('dblclick', function (e) { L.DomEvent.stop(e); removeVertex(m); });
    }
    function addVertex(latlng) {
      var m = L.marker(latlng, { icon: vIcon(), draggable: true });
      bindVertex(m);
      vertices.push(m);
      m.addTo(map);
      redraw(); sync();
    }
    function removeVertex(m) {
      var i = vertices.indexOf(m);
      if (i < 0) return;
      map.removeLayer(m);
      vertices.splice(i, 1);
      redraw(); sync();
    }
    function undo() {
      var m = vertices.pop();
      if (m) { map.removeLayer(m); redraw(); sync(); }
    }
    function clearAll() {
      vertices.forEach(function (m) { map.removeLayer(m); });
      vertices = [];
      redraw(); sync();
    }

    // Saqlangan chegarani yuklaymiz.
    saved.forEach(function (p) {
      var m = L.marker([p[0], p[1]], { icon: vIcon(), draggable: true });
      bindVertex(m);
      vertices.push(m);
      m.addTo(map);
    });
    redraw();
    if (saved.length >= 3) {
      try { map.fitBounds(poly.getBounds(), { padding: [24, 24] }); } catch (e) {}
    }

    // Xaritaga bosish — yangi nuqta.
    map.on('click', function (e) { addVertex(e.latlng); });

    // Boshqaruv paneli (Leaflet control).
    var Ctl = L.Control.extend({
      options: { position: 'topright' },
      onAdd: function () {
        var d = L.DomUtil.create('div', 'mh-editor-ctl');
        d.innerHTML =
          '<button type="button" data-a="undo" title="Oxirgi nuqtani olib tashlash">↩ Oxirgi</button>' +
          '<button type="button" data-a="clear" title="Hamma nuqtalarni tozalash">🗑 Tozalash</button>' +
          '<span class="mh-count"></span>';
        L.DomEvent.disableClickPropagation(d);
        L.DomEvent.disableScrollPropagation(d);
        d.querySelector('[data-a=undo]').addEventListener('click', undo);
        d.querySelector('[data-a=clear]').addEventListener('click', clearAll);
        return d;
      }
    });
    map.addControl(new Ctl());
    updateCount();

    setTimeout(function () { map.invalidateSize(); }, 250);
  }

  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);
})();
