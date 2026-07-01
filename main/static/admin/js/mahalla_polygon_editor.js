/* Mahalla chegarasini admin'da Leaflet + Leaflet.draw bilan tahrirlash.
   Xaritadagi poligon o'zgarsa, #id_boundary maydoni JSON [[lat,lng],...] bilan
   yangilanadi. center_lat/center_lng maydonlari ham avtomatik to'ldiriladi. */
(function () {
  function avg(pts, i) {
    return pts.reduce(function (s, p) { return s + p[i]; }, 0) / pts.length;
  }

  function init() {
    var ta = document.getElementById('id_boundary');
    var mapDiv = document.getElementById('mahallaEditorMap');
    if (!ta || !mapDiv || typeof L === 'undefined' || !L.Control || !L.Control.Draw) return;

    var DEFAULT = [40.1156, 64.5036]; // Shofirkon markazi
    var pts = [];
    try { pts = JSON.parse(ta.value || '[]') || []; } catch (e) { pts = []; }

    var center = pts.length ? [avg(pts, 0), avg(pts, 1)] : DEFAULT;
    var map = L.map('mahallaEditorMap').setView(center, pts.length ? 15 : 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '© OpenStreetMap'
    }).addTo(map);

    var drawn = new L.FeatureGroup();
    map.addLayer(drawn);

    if (pts.length >= 3) {
      var poly = L.polygon(pts, { color: '#3551d1', weight: 2, fillOpacity: 0.15 });
      drawn.addLayer(poly);
      try { map.fitBounds(poly.getBounds(), { padding: [24, 24] }); } catch (e) {}
    }

    var drawControl = new L.Control.Draw({
      edit: { featureGroup: drawn, remove: true },
      draw: {
        polygon: { allowIntersection: false, showArea: false },
        marker: false, polyline: false, circle: false,
        rectangle: false, circlemarker: false
      }
    });
    map.addControl(drawControl);

    function sync() {
      var layers = drawn.getLayers();
      var centerLat = document.getElementById('id_center_lat');
      var centerLng = document.getElementById('id_center_lng');
      if (!layers.length) { ta.value = ''; return; }
      var ll = layers[0].getLatLngs()[0];
      var arr = ll.map(function (p) {
        return [Math.round(p.lat * 1e6) / 1e6, Math.round(p.lng * 1e6) / 1e6];
      });
      ta.value = JSON.stringify(arr);
      if (centerLat && centerLng && arr.length) {
        centerLat.value = (Math.round(avg(arr, 0) * 1e6) / 1e6);
        centerLng.value = (Math.round(avg(arr, 1) * 1e6) / 1e6);
      }
    }

    map.on(L.Draw.Event.CREATED, function (e) { drawn.clearLayers(); drawn.addLayer(e.layer); sync(); });
    map.on(L.Draw.Event.EDITED, sync);
    map.on(L.Draw.Event.DELETED, sync);

    setTimeout(function () { map.invalidateSize(); }, 250);
  }

  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);
})();
