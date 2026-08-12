"""OLX.uz «Ish» provideri — vakansiya/rezyume e'lonlari (offers API).

OLX'ning umumiy offers API'si ish e'lonlarини ham qaytaradi. Bu yerда domen —
jobs, manba nomi 'OLX'. Narx (maosh) params.price'дан olinadi.
"""

from . import _http
from .base import ExternalListing, Provider, register
from .olx import OLX_API, _clean_price


@register
class OlxJobsProvider(Provider):
    key = 'olx_jobs'
    name = 'OLX'
    domain = 'jobs'
    categories = None

    def search(self, query, limit=5, category=None):
        query = (query or '').strip()
        if not query:
            return []
        data = _http.get_json(OLX_API, params={
            'offset': 0, 'limit': max(1, min(int(limit), 40)),
            'query': query, 'category_id': 4})  # 4 — OLX «Ish» ildiz toifasi
        if not data:
            return []
        out = []
        for item in (data.get('data') or []):
            v = self._parse(item)
            if v is not None:
                out.append(v)
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
            salary = ''
            for p in (item.get('params') or []):
                if p.get('key') == 'price':
                    salary = _clean_price((p.get('value') or {}).get('label') or '')
                    break
            loc = item.get('location') or {}
            city = ((loc.get('city') or {}) or {}).get('name') or ''
            return ExternalListing(title=title, url=url, source='OLX',
                                   price_label=salary, location=city, icon='💼')
        except Exception:  # noqa: BLE001
            return None
