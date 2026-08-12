"""Tayyor turgan (hozircha O'CHIRILGAN) ISH providerlari.

Ishonch.uz, OsonIsh.uz, Ish.uz, Rezume.uz, Jobs.uz, Ishga.uz, Bandlik.uz.

Nega o'chirilgan: bularning API'si TASDIQLANGAN emas (ko'pchiligi JavaScript SPA
yoki ochiq API bermaydi). Tasdiqlangan va ishlayotganlar — HH.uz va OLX «Ish».

Bu providerlar reyestrga qo'shiladi, lekin `ASSISTANT_EXTERNAL_JOB_PROVIDERS`
ro'yxatіда YO'Q — demak ishlamaydi (asistentni sekinlashtirmaydi). Har birининг
qidiruv endpointi tasdiqlangач:
  1) pastdagi `search()` ni to'ldiring (namuna: hh.py — rasmiy API, yoki
     avtoelon.py — HTML scraping),
  2) settings.py dagi ASSISTANT_EXTERNAL_JOB_PROVIDERS ga kalitini qo'shing.
Kod fail-safe: API bo'lmasa bo'sh ro'yxat qaytaradi — hech narsa buzilmaydi.
"""

from . import _http                       # noqa: F401 — to'ldirishда ishlatiladi
from .base import ExternalListing, Provider, register  # noqa: F401


class _JobStub(Provider):
    domain = 'jobs'
    categories = None
    def search(self, query, limit=5, category=None):
        return []                          # TODO: API tasdiqlangач to'ldiring


@register
class IshonchProvider(_JobStub):
    key = 'ishonch'
    name = 'Ishonch.uz'


@register
class OsonIshProvider(_JobStub):
    key = 'osonish'
    name = 'Oson Ish'


@register
class IshUzProvider(_JobStub):
    key = 'ish'
    name = 'Ish.uz'


@register
class RezumeProvider(_JobStub):
    key = 'rezume'
    name = 'Rezume.uz'


@register
class JobsUzProvider(_JobStub):
    key = 'jobs'
    name = 'Jobs.uz'


@register
class IshgaProvider(_JobStub):
    key = 'ishga'
    name = 'Ishga.uz'


@register
class BandlikProvider(_JobStub):
    key = 'bandlik'
    name = 'Bandlik.uz'
