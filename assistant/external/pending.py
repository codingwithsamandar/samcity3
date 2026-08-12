"""Tayyor turgan (hozircha O'CHIRILGAN) providerlar — Elon, Sof, Havas, Zoon, Anons.

Nega o'chirilgan: bularning barchasi OLX/Uybor kabi TASDIQLANGAN emas —
tekshiruvда quyidagilar aniqlandi:

  • elon.uz  — sayt so'rovга javob bermadi (o'chiq yoki bloklangan). API topilmadi.
  • sof.uz   — sayt so'rovга javob bermadi (o'chiq yoki bloklangan). API topilmadi.
  • havas.uz — supermarket (oziq-ovqat). Bu «e'lon» emas, sizning DELIVERY
               bo'limingizга yaqin. Agar kerak bo'lsa — delivery katalogiga ulash mantiqiyroq.
  • zoon.uz  — biznes/xizmatlar katalogi (salon, klinika, restoran). «Places»/
               «booking»ga yaqin, oldi-sotdi e'loni emas.
  • anons.uz — tadbirlar/kino/yangiliklar sayti. Oldi-sotdi umuman yo'q.

Shuning uchun ular reyestrga qo'shiladi, lekin `ASSISTANT_EXTERNAL_PROVIDERS`
ro'yxatіда YO'Q — demak ISHLAMAYDI (asistentni sekinlashtirmaydi). Har birining
API'sini tasdiqlagach:
  1) pastdagi `search()` ni to'ldiring (namuna: olx.py / uybor.py),
  2) settings.py dagi ASSISTANT_EXTERNAL_PROVIDERS ga kalitini qo'shing.
Kod fail-safe: aниq API bo'lmasa bo'sh ro'yxat qaytaradi — hech narsa buzilmaydi.
"""

from . import _http                       # noqa: F401 — to'ldirishда ishlatiladi
from .base import ExternalListing, Provider, register  # noqa: F401


@register
class ElonProvider(Provider):
    key = 'elon'
    name = 'Elon.uz'
    categories = None
    # TODO: elon.uz ishlaganда qidiruv API/HTML endpointini shu yerга yozing.
    def search(self, query, limit=5, category=None):
        return []


@register
class SofProvider(Provider):
    key = 'sof'
    name = 'Sof.uz'
    categories = None
    # TODO: sof.uz marketplace API topilganда to'ldiring (mahsulot qidiruvi).
    def search(self, query, limit=5, category=None):
        return []


@register
class HavasProvider(Provider):
    key = 'havas'
    name = 'Havas'
    categories = None
    # NOTE: Havas — oziq-ovqat do'koni. «E'lon» emas; delivery katalogiga mos.
    def search(self, query, limit=5, category=None):
        return []


@register
class ZoonProvider(Provider):
    key = 'zoon'
    name = 'Zoon'
    categories = None
    # NOTE: Zoon — biznes katalogi (salon/klinika/restoran). Places/booking ga mos.
    def search(self, query, limit=5, category=None):
        return []


@register
class AnonsProvider(Provider):
    key = 'anons'
    name = 'Anons'
    categories = None
    # NOTE: Anons — tadbir/kino/yangilik sayti. Oldi-sotdi e'loni yo'q.
    def search(self, query, limit=5, category=None):
        return []
