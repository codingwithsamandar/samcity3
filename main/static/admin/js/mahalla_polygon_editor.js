/* Mahalla chegarasini admin'da Leaflet + Leaflet.draw bilan tahrirlash.
   Xaritadagi poligon o'zgarsa, #id_boundary maydoni JSON [[lat,lng],...] bilan
   yangilanadi. Markaz (center_lat/center_lng) esa poligon centroididan avtomatik
   hisoblanadi — endi qo'lda kiritilmaydi (serverda save_model ham hisoblab qo'yadi). */
(function () {
  function avg(pts, i) {
    return pts.reduce(function (s, p) { return s + p[i]; }, 0) / pts.length;
  }
  function round6(n) { return Math.round(n * 1e6) / 1e6; }

  function init() {
    var ta = document.getElementById('id_boundary');
    var mapDiv = document.getElementById('mahallaEditorMap');
    if (!ta || !mapDiv || typeof L === 'undefined') return;

    var DEFAULT = [40.1156, 64.5036]; // Shofirkon markazi
    var pts = [];
    try { pts = JSON.parse(ta.value || '[]') || []; } catch (e) { pts = []; }

    var center = pts.length ? [avg(pts, 0), avg(pts, 1)] : DEFAULT;
    var map = L.map('mahallaEditorMap').setView(center, pts.length ? 15 : 14);

    // OSM asosiy qatlam; ba'zi tarmoqlarda bloklanadi — shunda Carto zaxirasiga o'tamiz.
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

    var drawn = new L.FeatureGroup();
    map.addLayer(drawn);

    if (pts.length >= 3) {
      var poly = L.polygon(pts, { color: '#3551d1', weight: 2, fillOpacity: 0.15 });
      drawn.addLayer(poly);
      try { map.fitBounds(poly.getBounds(), { padding: [24, 24] }); } catch (e) {}
    }

    function sync() {
      var layers = drawn.getLayers();
      var centerLat = document.getElementById('id_center_lat');
      var centerLng = document.getElementById('id_center_lng');
      if (!layers.length) { ta.value = ''; return; }
      var ll = layers[0].getLatLngs()[0];
      var arr = ll.map(function (p) { return [round6(p.lat), round6(p.lng)]; });
      ta.value = JSON.stringify(arr);
      // center_lat/center_lng endi formada yo'q; agar mavjud bo'lsa ham to'ldiramiz.
      if (centerLat && centerLng && arr.length) {
        centerLat.value = round6(avg(arr, 0));
        centerLng.value = round6(avg(arr, 1));
      }
    }

    // Leaflet.draw yuklangan bo'lsa — chizish/tahrirlash boshqaruvini qo'shamiz.
    if (L.Control && L.Control.Draw) {
      var drawControl = new L.Control.Draw({
        edit: { featureGroup: drawn, remove: true },
        draw: {
          polygon: { allowIntersection: false, showArea: false },
          marker: false, polyline: false, circle: false,
          rectangle: false, circlemarker: false
        }
      });
      map.addControl(drawControl);
      map.on(L.Draw.Event.CREATED, function (e) { drawn.clearLayers(); drawn.addLayer(e.layer); sync(); });
      map.on(L.Draw.Event.EDITED, sync);
      map.on(L.Draw.Event.DELETED, sync);
    }

    setTimeout(function () { map.invalidateSize(); }, 250);
  }

  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);
})();
