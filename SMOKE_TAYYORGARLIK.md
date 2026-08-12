# Smoke-test: tayyorgarlik tahlili (ishga tushirilmadi — kalit yo'q)

> Bu **oldindan (statik)** tahlil. Haqiqiy natija `SMOKE_NATIJA.md` ga yoziladi —
> uni `smoke_agent` buyrug'i kalit bilan ishga tushirilganda hosil qiladi.

## Holat

`AI_API_KEY` topilmadi — `.env`, `.env.production` va muhit o'zgaruvchilarida yo'q.
PROMPT_2.md B1 qoidasiga ko'ra: kod yozildi, **ishga tushirilmadi**, boshqa
provayder qidirilmadi.

### Kalitni qanday qo'yish

`.env` fayliga (loyiha ildizida, `sdev/settings.py` uni avtomatik o'qiydi):

```env
# Variant 1 — OpenAI (platform.openai.com/api-keys)
AI_PROVIDER=openai
AI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini

# Variant 2 — OpenRouter (openrouter.ai/keys) — bitta kalit bilan ko'p model,
# shuning uchun ikki modelni solishtirish uchun QULAYROQ
AI_PROVIDER=openrouter
AI_API_KEY=sk-or-...
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=openai/gpt-4o-mini
```

So'ng:

```bash
python manage.py seed_smoke
python manage.py smoke_agent --model gpt-4o-mini --verbose
python manage.py smoke_agent --model google/gemini-2.0-flash-001 \
    --provider openrouter --base-url https://openrouter.ai/api/v1
```

O'zbekcha uchun **OpenRouter tavsiya qilinadi**: bitta kalit bilan ikkala modelni
ham sinash mumkin (PROMPT_2 B5 talabi).

---

---

# ✅ YANGILANISH — 1 va 2-kamchilik HAL QILINDI

(b) varianti bajarildi. Quyidagi «kamchiliklar» bo'limi tarix uchun qoldirildi;
hozirgi holat shu yerda.

| Kamchilik | Holati |
|---|---|
| 1. Tool natijalari suhbatga kirmaydi (ID yo'qoladi) | ✅ **tuzatildi** |
| 2. `selection.py` ulanmagan | ✅ **ulandi** |
| 3. `taxi` va 10 bo'lim yo'q | ℹ️ kutilgan (0-to'lqin doirasi) |
| 4. **YANGI:** tool takrorlanishidan himoya yo'q edi | ✅ **tuzatildi** |

**Nima qilindi:**

1. `selection.create()` endi ro'yxatni faol `AgentTask.last_ui_ref` ga bog'laydi.
2. `prompts.build_dynamic_context()` keyingi navbatda ro'yxatni **ID'lari bilan**
   qo'shadi:
   ```
   [OXIRGI RO'YXAT] — hozir foydalanuvchi ekranida ko'rinib turibdi:
   1) Anor Fast Food — store_id=12
   2) Milano Pizza — store_id=13
   Bu ID'larni tool parametri sifatida ishlating. Ro'yxatni ovozda qayta sanamang.
   ```
   Erta qaytish (xarajat optimizatsiyasi) saqlandi — qo'shimcha LLM chaqiruvi yo'q.
3. `selection.resolve_items()` LLM'SIZ ishlaydi: foydalanuvchi «ikkinchisini»,
   «Milano ni», «eng arzonini» desa, kontekstga tayyor javob qo'shiladi:
   `[TANLOV] ... «Milano Pizza» (store_id=13). Qayta so'ramang — shuni ishlating.`
4. **Yangi topilma (zanjir testi ochdi):** `cart_add` `ui` qaytarmagani uchun halqa
   davom etardi va model o'sha chaqiruvni takrorlaganda savatga **5 marta**
   qo'shilardi (test: 2 o'rniga 10 dona). Asl topshiriqdagi 4.6-qoida
   («bir marta chaqirish») kodda yo'q ekan. Endi `agent.run` bir xil
   (bo'lim, amal, parametr) ikkinchi marta kelsa **qayta bajarmaydi** va halqani
   tugatadi.

**Isbot — `assistant/tests/test_chain.py` (11 ta test), jumladan to'liq oqim:**
do'kon qidirish → mahsulotlar (`store_id` kontekstdan) → savat (`product_id`
kontekstdan) → `propose_order` → tasdiq kartasi (85 000) → `confirm.execute` →
**1 ta buyurtma**. Har navbatda modelga aynan nima ko'rinishi tekshiriladi.

## Yangilangan bashorat

| # | Guruh | Avval | Endi |
|---|---|---|---|
| 5-8 | B (tanlov) | ❌ kafolatlangan xato | ✅ ishlashi kerak (6-8 `[TANLOV]` bilan) |
| 9-10 | C (savat) | ❌ kafolatlangan xato | ✅ ishlashi kerak |
| 1-4, 13, 15-20 | A, D, E, F | ❓ modelga bog'liq | ❓ modelga bog'liq — **haqiqiy sinov kerak** |

Ya'ni endi kod sababli kafolatlangan xato **qolmadi**. Smoke-testni ishga
tushirish mantiqiy — u endi modelning haqiqiy sifatini o'lchaydi.

---

## Kalitsiz ham aniqlangan 3 ta kamchilik (tarix — hal qilindi)

Quyidagilar model sifatiga **umuman bog'liq emas** — kodda funksiya yo'q. Ya'ni
kalit kelganda ham bu holatlar o'tmaydi. Sabab tugallangan tahlildan aniq.

### 1. ⛔ Tool natijalari suhbatga kirmaydi → `store_id`/`product_id` MODELGA YETMAYDI

**Eng jiddiy.** `agent.run()` da men qo'ygan «erta qaytish» optimizatsiyasi
(tool `ui` qaytarsa LLM ga qayta yubormaslik — xarajatni ikki barobar kamaytiradi)
kutilmagan yon ta'sirga olib kelgan.

Tekshirildi (mock LLM bilan, `find_store` → keyingi navbat):

```
1-navbat speech : "1 ta do'kon topdim, ekraningizda ko'rsatdim. Qaysi biridan olasiz?"
1-navbat ui     : [{'id': 'store:1', 'title': 'Anor Fast Food', 'store_id': 1, ...}]

2-navbatda model ko'radigan matn:  "store:" bormi? → YO'Q
```

`ui` FRONTEND ga ketadi, suhbat tarixiga esa faqat `speech` yoziladi — unda na
do'kon nomi, na ID bor. Natijada:

| Tool | Holati |
|---|---|
| `delivery.find_store` | ✅ ishlaydi |
| `delivery.list_products(store_id)` | ⛔ model `store_id` ni **hech qachon bila olmaydi** |
| `delivery.cart_add(product_id)` | ⛔ model `product_id` ni **hech qachon bila olmaydi** |
| `delivery.propose_order` | ⚠️ faqat savat boshqa yo'l bilan to'lgan bo'lsa |

**Ta'siri:** smoke-testning **B guruhi (5-8) va C guruhi (9-11)** — 20 tadan 7 tasi
— hech qanday modelda o'tmaydi. Section 9 dagi «qabul mezoni» oqimi (do'kon → mahsulot
→ savat → buyurtma) chatda **uzilgan**.

> Buni men 0-to'lqinda kiritganman va o'shanda «xarajat optimizatsiyasi» deb
> hujjatlashtirganman, lekin ID uzatilishini buzishini payqamaganman. Bu mening
> xatoyim.

**Yechim variantlari (qarorni siz qabul qilasiz — arxitektura o'zgarishi):**

- **(a) Erta qaytishni olib tashlash** — tool natijasi doim LLM ga qaytadi.
  Sodda, lekin har so'rov 2× LLM chaqiruvi (xarajat 2×) va sekinroq.
- **(b) Oxirgi ro'yxatni dinamik kontekstga qo'shish** *(tavsiya qilaman)* —
  `find_store` natijasi `AgentTask.last_ui_ref` ga yoziladi, keyingi navbatda
  `prompts.build_dynamic_context()` ixcham ro'yxat qo'shadi:
  `[OXIRGI RO'YXAT] 1) Anor Fast Food (store_id=12) 2) Milano Pizza (store_id=13)`.
  Erta qaytish saqlanadi (xarajat o'shanday), model ID ni biladi, `selection.py`
  ham ishlay boshlaydi. Infratuzilma tayyor — `remember_selection()` va
  `[OXIRGI RO'YXAT]` bloki allaqachon yozilgan, faqat **ulanmagan**.
- **(c) `select` tool'i** — model `select(ref, "ikkinchisi")` chaqiradi,
  `selection.resolve` yechadi. (b) bilan birga eng to'liq yechim.

### 2. ⛔ `selection.py` agent oqimiga umuman ulanmagan

`selection.resolve()` yozilgan va 13 ta test bilan qoplangan, lekin uni
**hech kim chaqirmaydi**:

```
$ grep -rn "selection.resolve" assistant/*.py assistant/tools/*.py
assistant/selection.py:184:   ... faqat docstring ichida
```

Ya'ni «ikkinchisini tanladim» / «anorni» / «eng arzonini» — 0-to'lqinda
**ishlamaydi**. 6, 7, 8-holatlar shu sababdan o'tmaydi.

Xuddi shunday ulanmagan: `AgentTask` agent oqimida **hech qachon yaratilmaydi**
(`task.get_or_create_active` chaqirilmaydi), `remember_selection()` ishlatilmaydi.

### 3. ℹ️ `taxi` va boshqa 10 bo'lim yo'q (bu kutilgan)

`build_llm_tools()` hozir **2 ta** bo'lim qaytaradi: `places`, `delivery`.
Bo'sh bo'limlar sxemaga kirmaydi, ya'ni model `taxi` ni ko'rmaydi — 18-holat
uchun aynan shu kerak (muloyim rad javobi). Bu kamchilik emas, 0-to'lqin doirasi.

---

## 20 holat bo'yicha oldindan bashorat

| # | Guruh | Bashorat | Sabab |
|---|---|---|---|
| 1-4 | A (marshrutlash) | ❓ modelga bog'liq | Haqiqiy sinov kerak — asosiy xavf 2-holat (`lavash` → `places` ga ketib qolishi) |
| 5 | B | ✅ ishlashi kerak | `find_store` + `card_list` |
| 6, 7, 8 | B (tanlov) | ❌ **kafolatlangan xato** | Kamchilik 1 va 2 |
| 9, 10 | C (savat) | ❌ **kafolatlangan xato** | `product_id` modelga yetmaydi |
| 11 | C (tasdiq) | ✅ ehtimol | Bajaruvchi tool umuman yo'q — model bajara olmaydi |
| 12 | D | ✅ ehtimol | `order_id` oladigan tool yo'q |
| 13 | D (injection) | ❓ haqiqiy sinov kerak | `wrap_untrusted` bor, lekin erta qaytish tufayli injection matni ko'pincha LLM ga umuman bormaydi |
| 14 | D (limit) | ✅ savat oldindan to'ldirilsa | `single_amount` server tomonda |
| 15-20 | E, F | ❓ modelga bog'liq | Til chidamliligi — haqiqiy sinov kerak |

**Xulosa:** hozir smoke-test ishga tushirilsa, eng yaxshi holatda ham **7 ta holat
(35%) kod sababli** yiqiladi. Avval 1 va 2-kamchilikni hal qilish mantiqiyroq —
aks holda pul sarflab, allaqachon ma'lum natijani tasdiqlaymiz.

---

## Tavsiya qilingan tartib

1. Siz **(b)** variantini (yoki boshqasini) tasdiqlaysiz → men ulayman (~kichik ish,
   infratuzilma tayyor).
2. Kalit qo'yiladi → `seed_smoke` + `smoke_agent` ikki modelda.
3. Haqiqiy natija `SMOKE_NATIJA.md` ga tushadi, prompt darajasidagi kamchiliklar
   tuzatiladi va test qayta ishlatiladi.
4. Shundan keyin 1-to'lqin.
