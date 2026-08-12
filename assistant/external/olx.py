"""OLX.uz provideri — ochiq offers API orqali e'lon qidiradi (scraping emas).

API: GET https://www.olx.uz/api/v1/offers/?query=<matn>&limit=<n>&offset=0
Umumiy marketplace — har qanday so'rovга mos (categories=None).
"""

from . import _http
from .base import ExternalListing, Provider, register

OLX_API = 'https://www.olx.uz/api/v1/offers/'


@register
class OlxProvider(Provider):
    key = 'olx'
    name = 'OLX'
    categories = None  # umumiy — hamma toifага

    def search(self, query, limit=5, category=None):
        query = (query or '').strip()
        if not query:
            return []
        data = _http.get_json(OLX_API, params={
            'offset': 0, 'limit': max(1, min(int(limit), 40)), 'query': query})
        if not data:
            return []
        out = []
        for item in (data.get('data') or []):
            listing = self._parse(item)
            if listing is not None:
                out.append(listing)
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _parse(item):
        try:
            title = (item.get('title') or '').strip()
            url = (item.get('url') or '').strip()
            if not title or not url:
                return None
            price_label = ''
            for p in (item.get('params') or []):
                if p.get('key') == 'price':
                    val = p.get('value') or {}
                    price_label = _clean_price(val.get('label') or '')
                    if not price_label and val.get('arranged'):
                        price_label = 'Kelishiladi'
                    break
            loc = item.get('location') or {}
            city = ((loc.get('city') or {}) or {}).get('name') or ''
            region = ((loc.get('region') or {}) or {}).get('name') or ''
            image = ''
            photos = item.get('photos') or []
            if photos:
                link = (photos[0] or {}).get('link') or ''
                image = (link.replace('{width}', '320').replace('{height}', '240')
                         if '{width}' in link else link)
            return ExternalListing(title=title, url=url, source='OLX',
                                   price_label=price_label,
                                   location=city or region, image=image)
        except Exception:  # noqa: BLE001
            return None


def _clean_price(label):
    label = (label or '').strip()
    return label.replace('сум', "so'm").replace('у.е.', 'u.e.') if label else ''
