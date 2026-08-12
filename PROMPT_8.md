# Claude Code uchun topshiriq — agent bron suhbatini OLDINGA SURSIN

Foydalanuvchi jonli sinadi: «sartaroshxonadan joy bron qil» → agent
sartaroshxonalarни ko'rsatdi va **TO'XTADI** — keyingi savolni (xizmat? vaqt?)
BERMADI. Foydalanuvchi so'zi: «manabu sartaroshxonalar bor, tamom, savol
bermadi».

Tool'lar to'g'ri (har biri `speech` da keyingi savolni beradi). Muammo:
**model bron oqimini oldinga surmayapti** — ro'yxatни ko'rsatib, vazifani
tugagan deb hisoblaydi.

Bu — PROMPT_4 dagi «erta qaytish» olib tashlanganining yon ta'siri: endi
yakuniy javobни MODEL yozadi, va u ko'p qadamli vazifani boshqarishни bilmaydi.

---

## Muammo 1 (ASOSIY) — model ko'p qadamli vazifani surmayapti

### Yechim A — prompt: bron = ko'p qadamli vazifa

`prompts.STATIC_PROMPT` ga aniq blok:

```
KO'P QADAMLI VAZIFANI OXIRIGACHA OLIB BOR
Ba'zi ishlar bir necha qadam: bron (joy → xizmat → vaqt → tasdiq), buyurtma
(do'kon → mahsulot → savat → tasdiq). Har qadamdan keyin TO'XTAMA — darhol
KEYINGI yetishmagan narsani so'ra. Ro'yxat ko'rsatgach «mana bor» deb tugatma;
«...topdim, qaysi birini tanlaysiz?» deb DAVOM et.

Vazifa tugamaguncha (tasdiq kartasигача) har javobing KEYINGI SAVOL bilan
tugasin. Foydalanuvchi tanlaganда — darhol keyingi qadamга o't:
  joy tanlandi → xizmatlarни ko'rsat va so'ra
  xizmat tanlandi → bo'sh vaqtlarни ko'rsat va so'ra
  vaqt tanlandi → tasdiq kartasини chiqar
Hech qachon vazifa o'rtasида to'xtab qolma.
```

### Yechim B — `[FAOL VAZIFA]` da keyingi qadamни ayt

`prompts.build_trusted_context()` da faol `AgentTask` bo'lsa, **keyingi
yetishmagan slot**ни aniq ko'rsat:

```
[FAOL VAZIFA] Bron qilyapsan. To'plangan: joy=Zamon Sartaroshxona.
KEYINGI QADAM: xizmatни so'ra (list_services chaqir).
```

Bu modelга «hozir qayerdaman va keyin nima» ни aniq aytadi. `booking.py`
tool'lari `_set_slots` bilan slotlarни yozadi — shuni o'qib, keyingi
yetishmaganини hisobla. Slot tartibi: `venue → service → time → (confirm)`.
`staff` ixtiyoriy (o'tkazib yuborilsin).

### Test
- Mock LLM: find_venue → keyin `[FAOL VAZIFA]` da «KEYINGI QADAM: xizmat» bo'lsin
- Slot to'lgach keyingi qadam yangilansin (service to'lsa → «vaqt so'ra»)

---

## Muammo 2 — bitta variant bo'lsa o'zi tanlasin

Bazada bitta sartaroshxona bor. Model bittalik ro'yxатни «tanlang» deб
ko'rsatyapti — g'aliz.

### Yechim

`booking.find_venue` (va `list_services`, `list_staff`) — natija **bitta**
bo'lsa:
- Uni avtomatik tanla (`_set_slots` ga yoz)
- `speech`: «Zamon Sartaroshxona topdim. Qaysi xizmat kerak?» (keyingi qadamга
  o't) — «tanlang» EMAS
- `ui` baribir ko'rsatilsin (foydalanuvchi ko'rsin), lekin savol keyingi
  qadam haqида bo'lsin

Ikki+ variant bo'lsa — hozirgidek «qaysi birini tanlaysiz?».

### Test
- Bitta venue → `speech` keyingi qadamни so'raydi, slot avtomatik to'ladi
- Ikki venue → «qaysi birini» so'raydi

---

## Muammo 3 — «bugun/ertaga» va vaqtni tabiiy tushunsin

Foydalanuvchi «11 da», «ertaga soat 3 da», «bugun kechqurun» deб aytadi.
`available_slots` va `propose_booking` bularни tushunsin.

- `_parse_day` «bugun/ertaga/YYYY-MM-DD» ni oladi — «11 da» kabi FAQAT vaqt
  bo'lsa, kun standart «bugun» bo'lsin
- Vaqt: «11 da» → 11:00, «3 da» → 15:00 (kunduzги mantiq: 1–8 → +12), «11:30»
  → 11:30. Kichik parser yoz yoki mavjudини kengaytir
- Bo'sh vaqtlar orasида bo'lmasa — muloyim ayt va yaqin vaqtlarни taklif qil

### Test
- «11 da» → 11:00, «3 da» → 15:00, «11:30» → 11:30
- Ish vaqtidан tashqари vaqt → muloyim rad + taklif

---

## Bajarish tartibi

1. Muammo 1 (prompt + [FAOL VAZIFA] keyingi qadam) — eng muhim
2. Muammo 2 (bitta variant avto-tanlov)
3. Muammo 3 (vaqt parser)
4. `python manage.py test assistant` (hozir 315)
5. ⚠️ **Jonli to'liq zanjir** (kvota bo'lsa) — bu safar OXIRIGACHA:
   «sartaroshxonadan joy bron qil» → xizmat so'raydimi → «soch olish» → vaqt
   so'raydimi → «11 da» → tasdiq kartasi chiqadimi. Har qadamни yoz.
   Kvota kam bo'lsa — bitta to'liq zanjir yetadi (5 navbat ≈ 12k token)

## Hisobotда kerak
1. Jonli: agent har qadamда keyingi savolни berdimi (5 navbat ketma-ket)
2. Qayerда to'xtadi yoki adashdi (bo'lsa)
3. Bitta variant avto-tanlov ishladimi
4. Vaqt «11 da» to'g'ri tushunildimi
5. Tasdiq kartаси to'g'ri summa (30 000) bilan chiqdimi
6. Nima hali g'aliz

## Chegara
- Yangi bo'lim qo'shma — faqat mavjud booking oqimini tuzat
- Arxitektura o'zgarishи bo'lsa — hisobotда ayt, o'zing qilma

`git commit` qilma. Ortiqcha maqtov kerak emas — nima ishlamadi, shuni ayt.

⚠️ Bu topshiriqning butun maqsadi — foydalanuvchi «sartaroshxona bron qil»
deб, OXIRIGACHA gaplashib, haqiqiy bron qila olishi. Jonli, to'liq zanjir
sinamasдан «tayyor» dema.
