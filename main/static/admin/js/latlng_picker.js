/* Admin: kenglik/uzunlik maydonlarini xaritadan bosib to'ldirish.
   `id_latitude` / `id_longitude` inputlarini avtomatik topib ishlaydi —
   qaysi model bo'lishidan qat'i nazar (Place, Taxist, Venue, Ad, HelpRequest, Store).

   Leaflet lokal vendordan yuklanadi (CDN UZ'da bloklanadi). Marker default rasm
   o'rniga divIcon bilan chiziladi — rasm/plagin kerak emas. */
(function () {
  'use strict';
  var DEFAULT_CENTER = [40.1156, 64.5036]; // Shofirkon

  function pinIcon() {
    return L.divIcon({
      className: 'llp-pin', html: '<div class="llp-pin-dot"></div>',
      iconSize: [18, 18], iconAnchor: [9, 9]
    });
  }

  function initPicker() {
    var latInput = document.getElementById('id_latitude');
    var lngInput = document.getElementById('id_longitude');
    if (!latInput || !lngInput || typeof L === 'undefined') return;
    var mapEl = document.getElementById('latlngPickerMap');
    if (!mapEl || mapEl.dataset.inited) return;
    mapEl.dataset.inited = '1';

    var hasValue = latInput.value && lngInput.value;
    var lat0 = parseFloat(latInput.value) || DEFAULT_CENTER[0];
    var lng0 = parseFloat(lngInput.value) || DEFAULT_CENTER[1];

    var map = L.map(mapEl).setView([lat0, lng0], hasValue ? 15 : 13);

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

    var marker = hasValue ? L.marker([lat0, lng0], { icon: pinIcon(), draggable: true }).addTo(map) : null;
    if (marker) marker.on('dragend', function () { setPoint(marker.getLatLng()); });

    function setPoint(latlng) {
      latInput.value = latlng.lat.toFixed(6);
      lngInput.value = latlng.lng.toFixed(6);
      if (marker) {
        marker.setLatLng(latlng);
      } else {
        marker = L.marker(latlng, { icon: pinIcon(), draggable: true }).addTo(map);
        marker.on('dragend', function () { setPoint(marker.getLatLng()); });
      }
    }
    map.on('click', function (e) { setPoint(e.latlng); });

    setTimeout(function () { map.invalidateSize(); }, 200);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPicker);
  } else {
    initPicker();
  }
})();
