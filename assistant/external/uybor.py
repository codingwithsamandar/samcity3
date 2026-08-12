"""Uybor.uz provideri — ochiq JSON API orqali ko'chmas mulk e'lonlari.

API: GET https://api.uybor.uz/api/v1/listings?limit=<n>&search=<matn>&order=-createDate
Javob: {"total": N, "results": [{id, operationType, description, price,
        priceCurrency, address, room, square, floor, media:[{url}], ...}]}

Faqat UY-JOY so'rovларида ishlaydi (kvartira, ijara, uy, hovli va h.k.).
"""

from . import _http
from .base import ExternalListing, Provider, register

UYBOR_API = 'https://api.uybor.uz/api/v1/listings'
_CUR = {'usd': 'u.e.', 'uzs': "so'm", 'usdt': 'u.e.'}


@register
class UyborProvider(Provider):
    key = 'uybor'
    name = 'Uybor'
    categories = ('uy_joy',)
    keywords = ('kvartira', 'uy-joy', 'uy joy', 'ijara', 'ijaraga', 'hovli',
                'xonadon', 'kvartir', 'novostroyka', 'kvartira', 'dom', 'arenda',
                'kommunalka', 'ofis', 'yer', 'uchastka')

    def search(self, query, limit=5, category=None):
        query = (query or '').strip()
        params = {'limit': max(1, min(int(limit), 20)), 'order': '-createDate'}
        if query:
            params['search'] = query
        data = _http.get_json(UYBOR_API, params=params)
        if not data:
            return []
        out = []
        for item in (data.get('results') or []):
            listing = self._parse(item)
            if listing is not None:
                out.append(listing)
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _parse(item):
        try:
            iid = item.get('id')
            if not iid:
                return None
            desc = (item.get('description') or '').replace('\n', ' ').strip()
            room = item.get('room')
            square = item.get('square')
            op = 'Ijara' if item.get('operationType') == 'rent' else 'Sotuv'
            bits = [op]
            if room:
                bits.append(f"{room}-xona")
            if square:
                bits.append(f"{square} m²")
            title = ', '.join(bits)
            if desc:
                title = f"{title} — {desc[:60]}"

            price = item.get('price')
            cur = _CUR.get((item.get('priceCurrency') or '').lower(), '')
            price_label = ''
            if price:
                price_label = f"{int(price):,}".replace(',', ' ')
                if cur:
                    price_label += f" {cur}"
                if item.get('operationType') == 'rent':
                    price_label += '/oy'

            image = ''
            media = item.get('media') or []
            if media:
                image = (media[0] or {}).get('url') or ''

            url = f"https://uybor.uz/listing/{iid}"
            return ExternalListing(title=title, url=url, source='Uybor',
                                   price_label=price_label,
                                   location=item.get('address') or '', image=image)
        except Exception:  # noqa: BLE001
            return None
