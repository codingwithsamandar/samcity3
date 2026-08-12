"""Avtoelon.uz provideri — avtomobil e'lonlari (server-rendered HTML).

Avtoelon ochiq JSON API bermaydi (token talab qiladi), lekin qidiruv sahifasini
server tomonда to'liq HTML qilib beradi. Shu HTML'дан regex bilan kartalar
ajratiladi. Karta havolasi: /uz/a/show/<id>.

Faqat AVTOMOBIL so'rovларида ishlaydi. Xato/markup o'zgarsa — bo'sh qaytaradi
(chat buzilmaydi), keyin regexни moslash kifoya.
"""

import re
import html as _htmlmod

from . import _http
from .base import ExternalListing, Provider, register

SEARCH_URL = 'https://avtoelon.uz/uz/qidiruv/'
_BASE = 'https://avtoelon.uz'

# Har bir e'lon havolasi: /uz/a/show/<id> . Anchor ichидаги matn — sarlavha.
_LINK_RE = re.compile(r'href="(/uz/a/show/(\d+))"[^>]*>(.*?)</a>', re.S)
_TAG_RE = re.compile(r'<[^>]+>')
_PRICE_RE = re.compile(r'([~\d][\d\s ]{2,})\s*(у\.е\.|у\.е|сум|so\'m|\$)', re.I)
_IMG_RE = re.compile(r'<img[^>]+src="(https://[^"]+\.(?:webp|jpe?g|png)[^"]*)"', re.I)


@register
class AvtoelonProvider(Provider):
    key = 'avtoelon'
    name = 'Avtoelon'
    categories = ('avtomobil',)
    keywords = ('mashina', 'moshina', 'avto', 'avtomobil', 'nexia', 'cobalt',
                'gentra', 'malibu', 'spark', 'damas', 'captiva', 'tracker',
                'onix', 'lacetti', 'matiz', 'kia', 'hyundai', 'chevrolet',
                'toyota', 'byd', 'mashinа')

    def search(self, query, limit=5, category=None):
        query = (query or '').strip()
        if not query:
            return []
        text = _http.get_text(SEARCH_URL, params={'text': query})
        if not text:
            return []
        return self._parse(text, limit)

    @staticmethod
    def _parse(text, limit):
        out, seen = [], set()
        for m in _LINK_RE.finditer(text):
            path, aid, inner = m.group(1), m.group(2), m.group(3)
            if aid in seen:
                continue
            seen.add(aid)
            title = _clean(inner)
            if not title or len(title) < 2:
                continue
            # Narx va rasmни havoladan keyingi ~600 belgi oynасидан qidiramiz.
            window = text[m.end():m.end() + 600]
            pm = _PRICE_RE.search(window)
            price_label = ''
            if pm:
                num = re.sub(r'[~\s ]', ' ', pm.group(1)).strip()
                unit = (pm.group(2).replace('сум', "so'm")
                        .replace('у.е.', 'u.e.').replace('у.е', 'u.e.'))
                price_label = f"{num} {unit}".strip()
            im = _IMG_RE.search(window) or _IMG_RE.search(text[max(0, m.start() - 600):m.start()])
            image = im.group(1) if im else ''
            out.append(ExternalListing(
                title=title[:100], url=_BASE + path, source='Avtoelon',
                price_label=price_label, location='', image=image))
            if len(out) >= limit:
                break
        return out


def _clean(fragment):
    return _htmlmod.unescape(_TAG_RE.sub(' ', fragment)).replace('\xa0', ' ').strip()
