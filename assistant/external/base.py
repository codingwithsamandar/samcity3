"""Tashqi provider protokoli va normallashtirilgan natija shakli.

Har bir tashqi sayt (OLX, Uybor, Avtoelon, …) o'z «provider»ini beradi. Provider
xom javobни BITTA umumiy shaklga — `ExternalListing` ga aylantiradi. Shu tufayli
`ads.search` qaysi saytdan kelganini bilishi shart emas: hammasi bir xil karta.

Provider `applies()` orqali o'zi qaysi so'rovларга mosligini aytadi — masalan
Avtoelon faqat avtomobil so'rovларида, Uybor faqat uy-joy so'rovларида ishlaydi.
Shu tufayli «velosiped» deganда avtomobil sayti behuda chaqirilmaydi.
"""

from dataclasses import dataclass


@dataclass
class ExternalListing:
    """Tashqi manbadan bitta e'lon/vakansiya — sayt-neytral shakl.

    Jobs (ish) uchun ham shu shakl: `price_label` — maosh, `location` — kompaniya/
    shahar, `icon` — 💼.
    """
    title: str
    url: str
    source: str = ''            # ko'rsatiladigan manba nomi, masalan 'OLX'
    price_label: str = ''       # narx/maosh matni: "1 400 000 so'm", "Kelishilgan"
    location: str = ''          # shahar / kompaniya
    image: str = ''             # rasm havolasi (ixtiyoriy)
    phone: str = ''             # aloqa raqami (ko'p manbalar API'da bermaydi)
    icon: str = '🌐'            # kartada ko'rinadigan belgi

    def to_card(self):
        sub = ' · '.join(p for p in (self.price_label, self.location) if p)
        card = {
            'title': (self.title or '')[:120],
            'subtitle': sub or self.source,
            'url': self.url,
            'tags': [self.source] if self.source else [],
            'icon': self.icon or '🌐',
        }
        if self.phone:
            card['phone'] = self.phone
        if self.image:
            card['image'] = self.image
        return card


class Provider:
    """Tashqi qidiruv provideri uchun asos.

    Meros oluvchi `key`, `name` ni belgilaydi va `search()` ni yozadi. `search`
    HECH QACHON istisno tashlamasin — tarmoq/parse xatosida bo'sh ro'yxat qaytarsin.

    Yo'naltirish (ixtiyoriy):
      categories — shu provider xizmat qiladigan `Ad` toifalari (None = hammasi).
      keywords   — so'rovда shu so'zlar bo'lsa, toifa mos kelmasa ham ishlaydi.
    """
    key = 'base'
    name = 'base'
    domain = 'ads'              # 'ads' (oldi-sotdi) yoki 'jobs' (ish)
    categories = None           # None → har qanday so'rovga mos
    keywords = ()               # qo'shimcha kalit so'zlar (toifasiz so'rov uchun)

    def applies(self, query, category=None):
        if self.categories is None:
            return True
        if category and category in self.categories:
            return True
        q = (query or '').lower()
        return any(k in q for k in self.keywords)

    def search(self, query, limit=5, category=None):
        raise NotImplementedError


# domain → {key → Provider nusxasi}
_REGISTRIES = {'ads': {}, 'jobs': {}}


def register(cls):
    """Provider klassini o'z domenидаги reyestrga qo'shadi (nusxa yaratib)."""
    _REGISTRIES.setdefault(cls.domain, {})[cls.key] = cls()
    return cls


def get_providers(keys=None, domain='ads'):
    """Domen bo'yicha providerlar. `keys=None` — hammasi; aks holda faqat berilganlar
    (sozlamадаги tartibда)."""
    reg = _REGISTRIES.get(domain, {})
    if keys is None:
        return list(reg.values())
    return [reg[k] for k in keys if k in reg]
