# Claude Code uchun topshiriq — smoke-test bloklari

Smoke-test birinchi marta haqiqiy model bilan ishga tushirildi (Groq,
`openai/gpt-oss-120b`) va **20 tadan 20 tasi yiqildi**. Diagnostika qilindi,
ikkita aniq sabab topildi. Bu topshiriq — o'shalarni tuzatish.

Diagnostika skripti: `debug_llm.py` (loyiha ildizida, tayyor turibdi).

---

## Muammo 1 — Cloudflare / User-Agent ✅ TUZATILDI

`urllib` ning standart `Python-urllib/3.x` UA'sini Cloudflare bot deb biladi va
so'rovni Groq API'gacha yetkazmasdan rad etadi (HTTP 403, `error code: 1010`).

**Empirik natija** (`debug_llm.py` dan):

```
❌ standart Python-urllib  → HTTP 403 (Cloudflare 1010)
✅ SamCity/1.0             → 200
✅ curl/8.4.0              → 200
✅ Chrome                  → 200
```

**Men `assistant/llm.py` da `_http_json()` ga UA qo'shdim** (`_user_agent()`,
`AI_USER_AGENT` env bilan sozlanadi).

**Sendan kerak:**
- Tuzatishni ko'rib chiq, to'g'ri joyda ekanini tasdiqla
- `_call_gemini()` ham `_http_json()` orqali ketadimi — tekshir, yo'q bo'lsa u
  ham UA olsin
- Test yoz: `_http_json` so'rovida `User-Agent` sarlavhasi borligini tekshirsin
  (tarmoqsiz — `urllib.request.Request` obyektini tekshirish yetarli)

⚠️ Bu ishlab chiqarishga ham tegishli edi — Render/Koyeb'dan Groq yoki
OpenRouter'ga chiqishda ham xuddi shu 403 bo'lardi.

---

## Muammo 2 — model `action` nomini funksiya nomi deb yuboradi ⛔ ASOSIY

**Xato** (Groq server tomonda rad etadi):

```
HTTP 400
"Tool call validation failed: attempted to call tool 'find_nearest'
 which was not in request.tools"

failed_generation:
{"name": "find_nearest", "arguments": {"action": "find_nearest",
                                       "category": "dorixona"}}
```

Model `name` ga `places` o'rniga `find_nearest` yozgan — lekin ayni paytda
`action: find_nearest` ni ham qo'ygan. Ya'ni ikki qavatli dizaynni yarim
tushungan.

**Muhim:** Groq buni **server tomonda** tekshiradi. Ya'ni `agent.py` da
«noto'g'ri nom kelsa to'g'rilab yuboraman» degan mudofaa **ishlamaydi** — tool
chaqiruvi bizgacha yetib kelmaydi, 400 qaytadi.

### Nega bunday bo'lgan (mening tahlilim)

`registry.build_llm_tools()` funksiya tavsifini shunday quradi:

```
• find_nearest: Eng yaqin joyni topadi — majburiy: category
• search_place: ...
• route_to: ...
```

Bu modelga **chaqiriladigan funksiyalar ro'yxati** bo'lib ko'rinadi. Model
o'sha ro'yxatdan bittasini tanlab, uni `name` ga qo'yadi.

### Tuzatish yo'nalishi (tartib bo'yicha sinab ko'r)

**2a. Funksiya tavsifini qisqartir, amallarni `action` parametriga ko'chir.**

Hozir amallar ro'yxati funksiya `description` ida. Uni `action` parametrining
`description` iga ko'chir. Funksiya tavsifi qisqa va aniq bo'lsin:

```
"Joy va manzil bilan bog'liq amallar. FUNKSIYA NOMI HAR DOIM 'places'.
 Bajariladigan amal `action` parametrida beriladi."
```

**2b. `action` uchun `enum` — allaqachon bormi tekshir, bo'lmasa qo'sh.**

**2c. Cheklangan parametrlarga JSON Schema `enum` qo'sh.**

`category: "dorixona"` kelgani ikkinchi muammo — model o'zbekcha so'z uzatgan.
Sabab: `category` sxemada oddiy `string`, faqat tavsifda «pharmacy, hospital…»
deb yozilgan. Prozadagi ko'rsatma yetarli emas — **sxemada `enum`** bo'lishi kerak.

`registry.tool()` dekoratoriga `enum` qo'llab-quvvatlashini qo'sh:

```python
params={
    "category": ("str", True, "Joy toifasi", ["pharmacy", "hospital", "bank", ...]),
}
```

Orqaga moslik saqlansin (4-elementli tuple ixtiyoriy). `_VALID_TYPES`
tekshiruvi buzilmasin. `places.find_nearest` va `delivery` tool'larida
mavjud kanonik ro'yxatlarni ishlat (`engine.CATEGORY_KEYWORDS` kalitlari).

**2d. `prompts.STATIC_PROMPT` ga qat'iy qoida qo'sh.**

Masalan (7-qoida sifatida):

```
FUNKSIYA CHAQIRISH QOIDASI
Funksiya nomi HAR DOIM bo'lim nomi: places, delivery, taxi, booking...
Amal nomi (find_nearest, cart_add, ...) HECH QACHON funksiya nomi emas —
u faqat `action` parametrining qiymati.
To'g'ri:   name="places",       arguments={"action": "find_nearest", ...}
Noto'g'ri: name="find_nearest", arguments={...}
```

---

## Bajarish tartibi

1. Muammo 1 ni tasdiqla + test yoz
2. Muammo 2 uchun 2a→2d ni bajar
3. `python debug_llm.py` — 3b bosqichi (hamma tool) o'tishi kerak
4. `python manage.py test assistant` — hammasi o'tsin (hozir 205 ta)
5. `python manage.py smoke_agent --model openai/gpt-oss-120b --verbose`
6. Natijani `SMOKE_NATIJA.md` ga yoz

## Agar hali ham yiqilsa — model tekshiruvi

`gpt-oss-120b` ochiq-vaznli model; tool-calling intizomi `gpt-4o-mini` dan
zaifroq. Agar 2a-2d dan keyin ham `name` xato kelsa, bu **bizning dizayn**
muammosimi yoki **model zaifligi** ekanini ajratish kerak.

Buning uchun ikkinchi model bilan yugurit:

```
python manage.py smoke_agent --model openai/gpt-oss-20b --verbose
```

Agar 20b ham xuddi shunday xato qilsa — model oilasi masalasi.
Agar 120b ishlab, 20b yiqilsa — model kuchi masalasi (kutilgan).

Har ikki holatda ham **xulosani hisobotga yoz**, o'zing arxitektura
o'zgartirma.

## ⚠️ Arxitektura qarori — o'zing qabul qilma

Agar 2a-2d yordam bermasa, keyingi variant «12 bo'lim + action» dizaynidan voz
kechib, har bir amalni alohida tool qilish (`places_find_nearest`,
`delivery_cart_add`…). Bu ~90 ta tool degani va biz undan ataylab qochgandik
(model 12 tadan ko'p tool orasida adashadi).

Bu **jiddiy arxitektura o'zgarishi**. O'zing qilma — hisobotda quyidagini ber:

- 2a-2d dan keyingi aniq natija (necha foiz to'g'ri)
- Ikki model solishtiruvi
- Tavsiyang va sababi
- Agar flatten kerak bo'lsa: qancha tool bo'ladi, qanday guruhlash mumkin
  (masalan faqat eng ko'p ishlatiladigan 15 tasini flatten qilib, qolganini
  bo'lim ostida qoldirish — aralash variant)

Men qaror qilaman.

---

## Yakunda ayt

1. Muammo 1 va 2 — tuzatildimi
2. `debug_llm.py` 3b bosqichi o'tadimi
3. Smoke-test: necha foiz to'g'ri (20 tadan nechta ✅)
4. Qaysi holatlar hali ham yiqiladi va sababi (bizmi / modelmi)
5. Arxitektura o'zgarishi kerakmi — halol baho

`git commit` qilma. Ortiqcha maqtov kerak emas — nima ishlamadi, shuni ayt.
