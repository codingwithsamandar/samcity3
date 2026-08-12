"""HH.uz (HeadHunter) provideri — rasmiy ochiq API orqali vakansiya qidiradi.

API: GET https://api.hh.ru/vacancies?text=<matn>&per_page=<n>&host=hh.uz
`host=hh.uz` — natijalar va havolalar hh.uz ga tegishli bo'ladi.
Javob: {"items": [{name, alternate_url, employer:{name}, area:{name},
        salary:{from,to,currency}}], "found": N}

Domen: jobs (ish). Har qanday kasb so'rovига mos.
"""

from . import _http
from .base import ExternalListing, Provider, register

HH_API = 'https://api.hh.ru/vacancies'
_CUR = {'UZS': "so'm", 'USD': 'u.e.', 'RUR': 'rub', 'RUB': 'rub'}


@register
class HHProvider(Provider):
    key = 'hh'
    name = 'HH.uz'
    domain = 'jobs'
    categories = None

    def search(self, query, limit=5, category=None):
        query = (query or '').strip()
        if not query:
            return []
        data = _http.get_json(HH_API, params={
            'text': query, 'per_page': max(1, min(int(limit), 20)),
            'host': 'hh.uz'})
        if not data:
            return []
        out = []
        for item in (data.get('items') or []):
            v = self._parse(item)
            if v is not None:
                out.append(v)
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _parse(item):
        try:
            title = (item.get('name') or '').strip()
            url = (item.get('alternate_url') or '').strip()
            if not title or not url:
                return None
            company = ((item.get('employer') or {}) or {}).get('name') or ''
            city = ((item.get('area') or {}) or {}).get('name') or ''
            loc = ' · '.join(p for p in (company, city) if p)
            salary = _salary(item.get('salary'))
            return ExternalListing(title=title, url=url, source='HH.uz',
                                   price_label=salary, location=loc, icon='💼')
        except Exception:  # noqa: BLE001
            return None


def _salary(s):
    if not s:
        return ''
    lo, hi = s.get('from'), s.get('to')
    cur = _CUR.get((s.get('currency') or '').upper(), s.get('currency') or '')
    def fmt(v):
        return f"{int(v):,}".replace(',', ' ')
    if lo and hi:
        return f"{fmt(lo)}–{fmt(hi)} {cur}".strip()
    if lo:
        return f"{fmt(lo)} {cur} dan".strip()
    if hi:
        return f"{fmt(hi)} {cur} gacha".strip()
    return ''
