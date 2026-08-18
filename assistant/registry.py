"""Tool reyestri — LLM chaqira oladigan amallar ro'yxati va ularni bajarish yo'li.

Nega alohida modul: agentning butun xavfsizlik modeli shu yerda majburlanadi.
Dasturchi tool yozadi, lekin uni «xavfsiz» qilishni UNUTA olmaydi — chunki:

  • `mutating=True` bo'lgan tool HECH QACHON to'g'ridan-to'g'ri bajarilmaydi.
    U faqat `PendingAction` (tasdiq kutayotgan amal) yaratadi. Haqiqiy bajarish
    alohida `@executor` funksiyasida, foydalanuvchi tasdiqlagandan keyin bo'ladi.
  • `user`, `district` LLM parametri EMAS — ular `ToolContext` orqali serverdan
    keladi. LLM bu maydonlarni ko'rmaydi ham, o'zgartira olmaydi ham.
  • Har bir chaqiruv oldidan `guard` tekshiradi (vakolat, limit), keyin `audit`ga
    yoziladi.

Bo'lim-tool modeli: LLM ga 90 ta emas, 12 ta tool beriladi. Har bo'lim bitta
funksiya, ichida `action` parametri (enum bilan cheklangan). Bu modelni
adashtirmaydi va prompt keshini barqaror saqlaydi.

Sxema hajmi: `tools_for()` so'rovga qarab faqat kerakli bo'limlarni beradi
(to'liq sxema ~3200 token va u HAR BIR LLM chaqiruvida ketadi). Tanlash
noaniq bo'lsa — to'liq sxema qaytadi, ya'ni agent hech qachon toolsiz qolmaydi.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# LLM ga ko'rsatiladigan 12 ta bo'lim. Tartib barqaror bo'lsin (kesh uchun).
SECTIONS = [
    'places', 'delivery', 'taxi', 'booking', 'ads', 'jobs',
    'community', 'account', 'merchant', 'payments', 'notifications', 'navigate',
]

# Bo'lim tavsiflari — LLM marshrutlash uchun (prompts.py da ham takrorlanadi,
# lekin bu yerda tool sxemasiga kiradi).
SECTION_DESC = {
    'places':   ("FAQAT manzil/joy topish — «qayerda?», «qanday boraman?». "
                 "Dorixona, shifoxona, bank, maktab, davlat idorasi. "
                 "Bu yerda hech narsa sotib olinmaydi va buyurtma qilinmaydi."),
    'delivery': ("Sotib olinadigan HAMMA narsa: ovqat, mahsulot, do'kon, savat, "
                 "buyurtma, yetkazib berish. «yeyishni xohlayman», «sotib "
                 "olmoqchiman», «buyurtma qil» — hammasi shu yerga."),
    'taxi':     ("Taksi: haydovchi/marshrut topish, narx, taksi chaqirish (buyurtma). "
                 "«taksi chaqir», «Buxoroga boraman»."),
    'booking':  ("Joy bron qilish: sartaroshxona, salon, restoran, to'yxona/zal, "
                 "klinika (shifokor qabuli). «sartaroshxona bron qil», «soch "
                 "oldirmoqchiman», «shifokorga yozilmoqchiman» — shu yerga. "
                 "Mening bronlarim, bekor qilish ham shu yerda."),
    'ads':      ("E'lonlar (oldi-sotdi marketplace): e'lon qidirish va YANGI e'lon "
                 "joylash. «mashina sotaman», «velosiped bormi»."),
    'jobs':     ("Ish e'lonlari (vakansiya) va rezyumelar: qidirish + joylash. "
                 "«ish qidiryapman», «xodim kerak»."),
    'community':("Mahalla xizmatlari: rasmiy e'lonlar, fuqaro murojaati (yo'l/suv/"
                 "svet muammosi), so'rovnoma va ovoz berish."),
    'account':  "Profil, buyurtmalar tarixi, sozlamalar.",
    'merchant': "Do'kon egasi paneli: mahsulot, buyurtmalar.",
    'payments': "Kommunal va boshqa to'lovlar.",
    'notifications': "Bildirishnomalar, eslatmalar.",
    'navigate': "Sayt bo'limiga o'tish (yo'naltirish).",
}


# ═══════════════════════════════════════════════════════════════════════════
#  KONTEKST — kim, qayerdan (LLM'dan EMAS, serverdan)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ToolContext:
    """Tool bajarilayotgan muhit — hammasi ISHONCHLI manba (server/sessiya)dan.

    LLM bu maydonlarning hech biriga ta'sir qila olmaydi. `user` — request'dan,
    `district` — `user.neighborhood.district`dan olinadi. Shu tufayli AI ni
    ko'ndirib boshqa foydalanuvchi nomidan ish qilish yoki boshqa tuman
    ma'lumotini ko'rish mumkin emas.
    """
    user: Any = None                 # request.user (anonim bo'lsa AnonymousUser)
    district: Any = None             # main.District yoki None
    session_key: str = ''
    task: Any = None                 # AgentTask yoki None
    request: Any = None              # HttpResponse request (CSRF/IP uchun)
    location: Optional[tuple] = None # (lat, lng) yoki None
    voice: bool = False              # ovozli rejimmi (javob uzunligiga ta'sir qiladi)

    @property
    def is_authenticated(self):
        u = self.user
        return bool(u is not None and getattr(u, 'is_authenticated', False))


def build_context(request, task=None, location=None, voice=False):
    """`request`dan ishonchli `ToolContext` quradi. district — user'dan keladi."""
    user = getattr(request, 'user', None)
    district = _district_of(user)
    session_key = ''
    try:
        if getattr(request, 'session', None) is not None:
            session_key = request.session.session_key or ''
            if not session_key:
                request.session.save()
                session_key = request.session.session_key or ''
    except Exception:
        session_key = ''
    return ToolContext(
        user=user, district=district, session_key=session_key,
        task=task, request=request, location=location, voice=voice,
    )


def _district_of(user):
    """Foydalanuvchi tumani: User.neighborhood → Neighborhood.district. Xatoga chidamli."""
    try:
        if user is None or not getattr(user, 'is_authenticated', False):
            return None
        nb = getattr(user, 'neighborhood', None)
        if nb is None:
            return None
        return getattr(nb, 'district', None)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  REYESTR — @tool va @executor
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ToolSpec:
    section: str
    action: str
    description: str
    params: dict            # {name: (type, required, desc)}
    mutating: bool
    auth_required: bool
    silent: bool
    owns: dict              # {param_name: 'app.Model'} — egalik tekshiruvi uchun
    func: Callable

    def key(self):
        return (self.section, self.action)


# (section, action) → ToolSpec
_TOOLS: dict = {}
# (section, action) → executor funksiyasi (tasdiqlangan mutating amalni bajaradi)
_EXECUTORS: dict = {}

_VALID_TYPES = {'int', 'str', 'float', 'number', 'bool'}


def tool(section, action, description, params=None, mutating=False,
         auth_required=False, silent=False, owns=None):
    """Tool'ni reyestrga qo'shadigan dekorator.

    params: {"nom": (tur, majburiymi, "tavsif")} yoki
            {"nom": (tur, majburiymi, "tavsif", ["ruxsat", "etilgan"])}.
            tur ∈ int/str/float/number/bool. To'rtinchi element — JSON Schema `enum`.
    mutating=True — natija MAJBURAN PendingAction ga aylanadi (bevosita bajarilmaydi).
    owns: {"order_id": "delivery.Order"} — guard obyekt shu userniki ekanini tekshiradi.
    """
    if section not in SECTIONS:
        raise ValueError(f"Noma'lum bo'lim: {section!r}. Ruxsat etilgan: {SECTIONS}")
    params = params or {}
    for pname, spec in params.items():
        if not (isinstance(spec, tuple) and len(spec) in (3, 4)):
            raise ValueError(f"{section}.{action}: '{pname}' spetsifikatsiyasi "
                             f"(tur, majburiymi, tavsif[, enum]) bo'lishi kerak")
        if spec[0] not in _VALID_TYPES:
            raise ValueError(f"{section}.{action}: '{pname}' turi noto'g'ri: {spec[0]!r}")
        if len(spec) == 4 and not isinstance(spec[3], (list, tuple)):
            raise ValueError(f"{section}.{action}: '{pname}' enum ro'yxat bo'lishi kerak")

    def deco(func):
        spec = ToolSpec(
            section=section, action=action, description=description,
            params=params, mutating=mutating, auth_required=auth_required,
            silent=silent, owns=owns or {}, func=func,
        )
        if spec.key() in _TOOLS:
            raise ValueError(f"Tool takroran ro'yxatdan o'tkazilmoqda: {spec.key()}")
        _TOOLS[spec.key()] = spec
        return func

    return deco


def executor(section, action):
    """Tasdiqlangan mutating amalni HAQIQATDA bajaradigan funksiyani ro'yxatga oladi.

    Bu funksiya LLM ga KO'RINMAYDI — faqat `confirm.execute()` chaqiradi, ya'ni
    foydalanuvchi tasdiq tugmasini bosgandan keyin. Imzo: (payload, user) → dict.
    """
    def deco(func):
        _EXECUTORS[(section, action)] = func
        return func
    return deco


def get_tool(section, action):
    return _TOOLS.get((section, action))


def get_executor(section, action):
    return _EXECUTORS.get((section, action))


def all_tools():
    return dict(_TOOLS)


# ═══════════════════════════════════════════════════════════════════════════
#  LLM TOOL SXEMASI (OpenAI `tools` formati)
# ═══════════════════════════════════════════════════════════════════════════

_TYPE_TO_JSON = {'int': 'integer', 'float': 'number', 'number': 'number',
                 'str': 'string', 'bool': 'boolean'}


def param_parts(spec_tuple):
    """Parametr spetsifikatsiyasini ochadi: (tur, majburiymi, tavsif, enum|None).

    3- va 4-elementli tuple ikkalasini ham qo'llab-quvvatlaydi (orqaga moslik).
    """
    ptype, required, desc = spec_tuple[0], spec_tuple[1], spec_tuple[2]
    enum = list(spec_tuple[3]) if len(spec_tuple) == 4 else None
    return ptype, required, desc, enum


# `action` tavsifining sarlavhasi. Belgilarni bir marta tushuntiramiz — keyin
# har amalda «tasdiq talab qiladi», «majburiy: ...» so'zlarini takrorlamaymiz
# (78 ta amal × 12 token = bekorga ketgan kontekst).
_ACTION_HEADER = ("Bajariladigan amal. Satr ko'rinishi «• amal [majburiy "
                  "parametrlar]: vazifasi», ⚠️ = tasdiq talab qiladi:\n")


def _section_schema(section, actions):
    """Bitta bo'lim uchun OpenAI `tools` elementini quradi."""
    # ⚠️ Amallar ro'yxati ATAYLAB funksiya tavsifida EMAS, `action`
    # parametrining tavsifida. Aks holda model amallar ro'yxatini
    # «chaqiriladigan funksiyalar» deb tushunib, `name` ga bo'lim o'rniga
    # amal nomini yozadi (Groq buni server tomonda rad etadi:
    # "attempted to call tool 'find_nearest' which was not in request.tools").
    action_lines, seen_params = [], {}
    for aname in sorted(actions.keys()):
        spec = actions[aname]
        tag = '⚠️' if spec.mutating else ''
        req = [p for p, s in spec.params.items() if param_parts(s)[1]]
        req_txt = f" [{', '.join(req)}]" if req else ''
        action_lines.append(f"• {aname}{tag}{req_txt}: {spec.description}")

        for pname, pspec in spec.params.items():
            ptype, _required, pdesc, penum = param_parts(pspec)
            # Bir nomdagi parametr turli amallarda uchrasa — birlashtiramiz.
            # Tavsif bir xil bo'lsa MATN TAKRORLANMAYDI, faqat amal nomi
            # qo'shiladi: «[post_job, post_resume] aloqa telefoni».
            if pname not in seen_params:
                seen_params[pname] = {
                    'type': _TYPE_TO_JSON.get(ptype, 'string'),
                    # tavsif → uni talab qiladigan amallar (tartib barqaror)
                    '_descs': {pdesc: [aname]},
                    # Sxemadagi enum — prozadagi ko'rsatmadan ancha kuchli:
                    # modelning o'zbekcha so'z («dorixona») uzatishini to'xtatadi.
                    '_enum': list(penum or []),
                }
            else:
                prop = seen_params[pname]
                prop['_descs'].setdefault(pdesc, []).append(aname)
                if penum:
                    prop['_enum'] = sorted(set(prop['_enum']) | set(penum))

    properties = {
        'action': {
            'type': 'string',
            'enum': sorted(actions.keys()),
            'description': _ACTION_HEADER + "\n".join(action_lines),
        }
    }
    for pname, prop in seen_params.items():
        out = {'type': prop['type'],
               'description': "; ".join(f"[{', '.join(anames)}] {desc}"
                                        for desc, anames in prop['_descs'].items())}
        if prop['_enum']:
            out['enum'] = prop['_enum']
        properties[pname] = out

    return {
        'type': 'function',
        'function': {
            'name': section,
            # Qisqa va aniq — model «bu funksiyaning nomi» deb adashmasin.
            'description': (
                f"{SECTION_DESC.get(section, section)}\n"
                f"FUNKSIYA NOMI HAR DOIM '{section}' — amal `action` parametrida."),
            'parameters': {
                'type': 'object',
                'properties': properties,
                'required': ['action'],
                'additionalProperties': False,
            },
        },
    }


def build_llm_tools(sections=None):
    """Bo'limlar uchun JSON Schema (OpenAI `tools`) qaytaradi.

    Har bo'lim bitta funksiya. `action` — shu bo'limdagi amallar `enum`i (majburiy).
    Qolgan parametrlar birlashtiriladi; qaysi amalga qaysi kerakligi tavsifda
    ko'rsatiladi (JSON Schema amal bo'yicha shartli majburiylikni qo'llab-quvvatlamaydi).

    `sections=None` — HAMMASI (eski xatti-harakat). Ro'yxat berilsa faqat o'shalar
    qaytadi (`select_sections` ni qarang): butun sxema ~3 ming token, bitta so'rovga
    esa odatda 2-3 bo'lim yetadi.

    ⚠️ Tartib HAR DOIM `SECTIONS` bo'yicha — bir xil to'plam bir xil JSON beradi,
    ya'ni prompt keshi bo'lim to'plami darajasida saqlanadi.
    """
    allow = None if sections is None else set(sections)
    tools = []
    for section in SECTIONS:
        if allow is not None and section not in allow:
            continue
        actions = {k[1]: v for k, v in _TOOLS.items() if k[0] == section}
        if not actions:
            continue
        tools.append(_section_schema(section, actions))
    return tools


# ═══════════════════════════════════════════════════════════════════════════
#  BO'LIM TANLASH — so'rovga qarab faqat keraklisini yuborish
# ═══════════════════════════════════════════════════════════════════════════
#
# Nega: butun sxema ~3 ming token, va u HAR BIR LLM chaqiruvida ketadi (agent
# halqasi 5 qadamgacha). Bitta so'rovga esa deyarli har doim 1-2 bo'lim yetadi
# («sartaroshxona bron qil» → booking). Tanlash EVRISTIK, shuning uchun ikki
# xavfsizlik qoidasi bor:
#
#   1. HECH NARSA topilmasa — HAMMA bo'lim yuboriladi. Kam tokenli, lekin
#      kerakli tool'siz qolgan agent — yomonroq: u tool o'rniga TO'QIB javob
#      berishga o'tadi. Shubhada har doim ko'proq tomonga og'amiz.
#   2. places ↔ delivery HAR DOIM birga ketadi. Ular orasidagi chegara
#      («qayerda?» ↔ «sotib olaman») modelning eng ko'p adashadigan joyi;
#      bittasini olib qo'yish adashishni tuzatmaydi — yashiradi.
#
# O'zaklar (qo'shimchasiz) yoziladi: «dorixona/dorixonani/dorixonaga» → 'dorixon'.
_SECTION_HINTS = {
    'places': ('qayer', 'manzil', 'yaqin', 'dorixon', 'aptek', 'shifoxon',
               'kasalxon', 'poliklinik', 'bankomat', 'maktab', "bog'ch", 'bogch',
               'pochta', 'hokimiy', 'idora', 'mehmonxon', 'muzey', 'yo\'l ko\'rsat',
               'qanday bor', 'qayerda'),
    'delivery': ('ovqat', 'yeyish', 'och qol', 'taom', 'lavash', 'somsa', 'pitsa',
                 'burger', 'kabob', 'shashlik', "do'kon", 'dokon', 'magazin',
                 'mahsulot', 'savat', 'buyurtma', 'yetkaz', 'dostavka',
                 'sotib ol', 'olib kel', 'non ', 'suv ', 'sut ', 'meva'),
    'taxi': ('taksi', 'taxi', 'haydovchi', 'marshrut', 'safar', 'olib bor'),
    'booking': ('bron', 'band qil', 'sartaroshxon', 'soch ol', 'soch qir',
                'salon', "go'zallik", 'gozallik', 'restoran', 'kafe', 'stol',
                "to'yxon", 'toyxon', 'zal ', 'navbat', 'usta', 'yozil'),
    'ads': ("e'lon", 'elon', 'sotaman', 'sotiladi', 'olx', 'kvartira', 'ijara',
            'velosiped', 'avtomobil', 'mashina sot', 'arzon'),
    'jobs': ('ish qidir', 'ish top', 'ish bor', 'ishga', 'vakansiy', 'rezyume',
             'rezume', 'xodim', 'ishchi kerak', 'maosh', 'oylik', 'lavozim',
             'hh.uz', 'kasb'),
    'community': ('mahalla', 'rais', 'murojaat', 'shikoyat', "so'rovnoma",
                  'sorovnoma', 'ovoz ber', "yig'ilish", 'svet', 'chiroq',
                  'tozalik', 'obodonlash', 'gaz '),
    'account': ('profil', 'ismim', 'mening ism', 'buyurtmalarim', 'bronlarim',
                "e'lonlarim", 'elonlarim', 'sozlama', 'hisobim', 'raqamim',
                'safarlarim'),
}

# Chegarasi eng sirg'aluvchan juftlik — bittasi tanlansa ikkinchisi ham ketadi.
_COMPANIONS = {'places': ('delivery',), 'delivery': ('places',)}


def _normalize(text):
    """Kalit so'z qidirish uchun matnni bir ko'rinishga keltiradi."""
    s = (text or '').lower()
    for ch in ('ʻ', 'ʼ', '‘', '’', '`', '´'):
        s = s.replace(ch, "'")
    return ' ' + ' '.join(s.split()) + ' '


def select_sections(message, task=None, history=None):
    """So'rovga tegishli bo'lim nomlarini qaytaradi (`build_llm_tools` uchun).

    Topa olmasa — HAMMASI (`SECTIONS`). Ya'ni bu funksiya faqat ARZONLASHTIRADI,
    agentning imkoniyatini kamaytirmaydi: noaniq holatda eski (to'liq) xatti-
    harakat qaytadi.

    task — faol vazifa: uning `goal`i bo'lim nomi (`selection.create` shunday
    yozadi), demak yarim qolgan oqim davom etsin («ha», «birinchisini» kabi
    kalit so'zsiz javoblarda YAGONA ishonchli ishora shu).
    """
    text = _normalize(message)
    # Oxirgi 2 navbat ham qo'shiladi: «ikkinchisini» degan javobda mavzu
    # faqat oldingi gapda qoladi.
    for h in (history or [])[-2:]:
        if isinstance(h, dict) and h.get('content'):
            text += _normalize(h['content'])

    chosen = {s for s, hints in _SECTION_HINTS.items()
              if any(h in text for h in hints)}

    goal = getattr(task, 'goal', '') or ''
    if goal in SECTIONS:
        chosen.add(goal)

    if not chosen:
        return list(SECTIONS)

    for s in list(chosen):
        chosen.update(_COMPANIONS.get(s, ()))
    # Tartib har doim SECTIONS bo'yicha — bir xil to'plam bir xil sxema (kesh).
    return [s for s in SECTIONS if s in chosen]


def tools_for(message, task=None, history=None):
    """So'rovga mos LLM tool sxemasi. Agent shuni chaqiradi.

    Tanlangan bo'limlarda bitta ham ro'yxatdan o'tgan amal bo'lmasa (masalan
    `taxi` topildi, lekin TAXI_ENABLED=False — modul umuman import qilinmagan),
    to'liq sxemaga qaytamiz: LLM ga BO'SH tool ro'yxati berish eng yomon variant
    — model tool o'rniga javobni to'qishga o'tadi.
    """
    tools = build_llm_tools(select_sections(message, task=task, history=history))
    return tools or build_llm_tools()


# ═══════════════════════════════════════════════════════════════════════════
#  PARAMETRLARNI TEKSHIRISH VA MAJBURLASH
# ═══════════════════════════════════════════════════════════════════════════

class ParamError(Exception):
    """Noto'g'ri/yetishmayotgan/ortiqcha parametr — foydalanuvchiga aniq xato."""


def _coerce_one(name, ptype, value):
    """Bitta parametrni kerakli turga keltiradi. int("5")→5, int("abc")→ParamError."""
    if value is None:
        return None
    try:
        if ptype == 'int':
            if isinstance(value, bool):
                raise ValueError
            return int(value)
        if ptype in ('float', 'number'):
            if isinstance(value, bool):
                raise ValueError
            return float(value)
        if ptype == 'bool':
            if isinstance(value, bool):
                return value
            s = str(value).strip().lower()
            if s in ('1', 'true', 'ha', 'yes', 'ok'):
                return True
            if s in ('0', 'false', 'yoq', 'no'):
                return False
            raise ValueError
        # str
        return str(value)
    except (ValueError, TypeError):
        raise ParamError(f"«{name}» qiymati noto'g'ri (kutilgan tur: {ptype})")


def validate_params(spec, params):
    """`params`ni `spec.params`ga solishtiradi, turlarni majburlaydi.

    Noma'lum parametr, yetishmayotgan majburiy parametr yoki noto'g'ri tur →
    `ParamError`. Muvaffaqiyatda tozalangan (coerced) lug'at qaytaradi.
    """
    params = params or {}
    if not isinstance(params, dict):
        raise ParamError("Parametrlar lug'at (obyekt) bo'lishi kerak")

    allowed = set(spec.params.keys())
    extra = set(params.keys()) - allowed
    if extra:
        raise ParamError(f"Ortiqcha parametr(lar): {', '.join(sorted(extra))}")

    cleaned = {}
    for pname, pspec in spec.params.items():
        ptype, required, _desc, _enum = param_parts(pspec)
        if pname not in params or params[pname] is None:
            if required:
                raise ParamError(f"«{pname}» majburiy parametr yetishmayapti")
            continue
        # ⚠️ `enum` ATAYLAB bu yerda MAJBURLANMAYDI. U sxemada modelni to'g'ri
        # qiymatga yo'naltirish uchun. Model baribir «dorixona» deb yuborsa,
        # tool'ning o'z normalizatsiyasi (masalan engine.detect_category) uni
        # tushunadi — xato qaytarishdan ko'ra foydaliroq.
        cleaned[pname] = _coerce_one(pname, ptype, params[pname])
    return cleaned


# ═══════════════════════════════════════════════════════════════════════════
#  DISPATCH — guard → tool → (mutating? PendingAction : natija) → audit
# ═══════════════════════════════════════════════════════════════════════════

def _err(status, reply, error=''):
    return {'ok': False, 'result_status': status, 'error': error or status,
            'reply': reply, 'speech': reply, 'ui': None, 'silent': False}


def dispatch(section, action, params, ctx):
    """Bitta tool chaqiruvini boshidan oxirigacha boshqaradi. HECH QACHON istisno
    tashlamaydi — har doim {ok, ...} lug'at qaytaradi (chat oqimi buzilmasin).
    """
    import time
    from . import guard

    started = time.monotonic()
    spec = get_tool(section, action)
    if spec is None:
        res = _err('error', "Bunday amalni bajara olmayman.",
                   f"noma'lum tool: {section}.{action}")
        guard.audit(ctx, section, action, params or {}, res, 0)
        return res

    # 1) Parametrlarni tekshirish/majburlash
    try:
        cleaned = validate_params(spec, params)
    except ParamError as e:
        res = _err('error', str(e), f"param: {e}")
        guard.audit(ctx, section, action, params or {}, res,
                    int((time.monotonic() - started) * 1000))
        return res

    # 2) Guard: vakolat, egalik, limit
    denial = guard.authorize(spec, cleaned, ctx)
    if denial is not None:
        guard.audit(ctx, section, action, cleaned, denial,
                    int((time.monotonic() - started) * 1000))
        return denial

    # 3) Tool'ni bajarish
    try:
        raw = spec.func(ctx, **cleaned)
    except Exception as e:  # noqa: BLE001 — chat oqimini buzmaymiz
        res = _err('error', "Amalni bajarishda xatolik yuz berdi.", f"{type(e).__name__}: {e}")
        guard.audit(ctx, section, action, cleaned, res,
                    int((time.monotonic() - started) * 1000))
        return res

    raw = raw or {}

    # 4) mutating=True → bevosita bajarilmaydi, PendingAction yaratiladi
    if spec.mutating:
        res = _to_pending(ctx, spec, raw)
        guard.audit(ctx, section, action, cleaned, res,
                    int((time.monotonic() - started) * 1000))
        return res

    # 5) Oddiy (o'qish yoki savat kabi pulsiz) natija
    res = {
        'ok': raw.get('ok', True),
        'result_status': 'ok',
        'speech': raw.get('speech', ''),
        'ui': raw.get('ui'),
        'silent': bool(raw.get('silent', spec.silent)),
    }
    if 'data' in raw:
        res['data'] = raw['data']
    guard.audit(ctx, section, action, cleaned, res,
                int((time.monotonic() - started) * 1000))
    return res


def _to_pending(ctx, spec, raw):
    """Mutating tool natijasini PendingAction ga aylantiradi.

    Tool `propose(...)` orqali {exec_action, payload, summary_card, amount, speech}
    qaytarishi SHART. Aks holda — dasturchi xatosi: hech narsa bajarilmaydi.
    """
    from . import confirm, guard

    exec_action = raw.get('exec_action')
    if not exec_action:
        # Mutating tool tasdiq strukturasini qaytarmadi — xavfsiz tomonga o'tamiz.
        if raw.get('ok') is False:
            # Tool ataylab xato qaytardi (masalan savat bo'sh) — shuni ko'rsatamiz.
            return {
                'ok': False, 'result_status': 'error',
                'speech': raw.get('speech', "Amalni bajara olmadim."),
                'ui': raw.get('ui'), 'silent': False,
            }
        return _err('error', "Amalni tasdiqqa tayyorlab bo'lmadi.",
                    f"mutating tool exec_action qaytarmadi: {spec.key()}")

    if get_executor(spec.section, exec_action) is None:
        return _err('error', "Amalni bajaruvchi topilmadi.",
                    f"executor yo'q: {spec.section}.{exec_action}")

    amount = raw.get('amount', 0) or 0
    # Summa limitini tasdiqdan OLDIN tekshiramiz (limitdan oshsa kartani ko'rsatmaymiz).
    lim = guard.check_amount(ctx, amount)
    if lim is not None:
        return lim

    pa = confirm.create_pending(
        ctx, section=spec.section, action=exec_action,
        payload=raw.get('payload', {}) or {},
        summary_card=raw.get('summary_card', {}) or {},
        amount=amount,
    )
    if pa is None:
        return _err('error', "Tasdiq amalini yaratib bo'lmadi.", "create_pending=None")

    # Tasdiq kartasiga pending_id va havolalarni to'ldiramiz (frontend POST qiladi).
    card = raw.get('summary_card') or {'type': 'text'}
    if isinstance(card, dict) and card.get('type') in ('confirm_payment', 'confirm'):
        card['pending_id'] = str(pa.id)
        card.setdefault('action_url', f'/ai/confirm/{pa.id}/')
        card.setdefault('cancel_url', f'/ai/cancel/{pa.id}/')

    return {
        'ok': True, 'result_status': 'pending',
        'speech': raw.get('speech', "Tasdiqlashingizni kutyapman."),
        'ui': card,
        'pending_id': str(pa.id),
        'silent': False,
    }


def propose(exec_action, payload, summary_card, amount=0, speech=''):
    """Mutating tool ichida ishlatiladi: tasdiq uchun strukturani quradi.

    Bu funksiyani ishlatish — mutating tool haqiqatda hech narsa bajarmasligini
    kafolatlaydi. U faqat «nima qilinishi kerakligini» tasvirlaydi; bajarish
    `@executor` da, tasdiqdan keyin bo'ladi.
    """
    return {
        'exec_action': exec_action,
        'payload': payload or {},
        'summary_card': summary_card or {},
        'amount': amount or 0,
        'speech': speech,
    }
