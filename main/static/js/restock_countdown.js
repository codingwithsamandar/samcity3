/**
 * "Tugagan" mahsulotlar uchun qayta kelish vaqtigacha sekundomer.
 * Har bir [data-restock] elementi ISO vaqt (data-restock) saqlaydi;
 * server vaqti bilan taxminiy farq data-server-now orqali hisobga olinadi.
 */
(function () {
  function fmt(ms) {
    if (ms <= 0) return null;
    var s = Math.floor(ms / 1000);
    var d = Math.floor(s / 86400); s -= d * 86400;
    var h = Math.floor(s / 3600); s -= h * 3600;
    var m = Math.floor(s / 60); s -= m * 60;
    var parts = [];
    if (d > 0) parts.push(d + ' kun');
    if (h > 0 || d > 0) parts.push(h + ' soat');
    parts.push(m + ' daqiqa');
    return parts.join(' ');
  }

  function tick(el, targetMs, offsetMs) {
    var remaining = targetMs - (Date.now() + offsetMs);
    var label = fmt(remaining);
    el.textContent = label ? (label + ' qoldi') : 'Tez orada kutilmoqda';
  }

  function init() {
    var els = document.querySelectorAll('[data-restock]');
    if (!els.length) return;
    var serverNow = document.body.getAttribute('data-server-now');
    var offsetMs = serverNow ? (new Date(serverNow).getTime() - Date.now()) : 0;

    els.forEach(function (el) {
      var target = new Date(el.getAttribute('data-restock')).getTime();
      if (isNaN(target)) return;
      tick(el, target, offsetMs);
      setInterval(function () { tick(el, target, offsetMs); }, 60000);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
