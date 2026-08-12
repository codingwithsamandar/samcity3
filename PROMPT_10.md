# Claude Code uchun topshiriq — faol vazifa bo'lsa engine chekinsin (suhbat o'rtasida uzilyapti)

Jonli sinov (kirgan, brauzer orqали, gpt-4.1-mini):
- «sartaroshxonadan joy bron qilib ber» → ✅ agent bron boshladi, xizmatlarни
  ko'rsatdi: «Qaysi xizmatni tanlaysiz?»
- «soch olish» → ❌ agent O'RNIGA yana sartaroshxona MANZILLARI chiqdi.
  Bron suhbati UZILDI.

PROMPT_9 birinchi xabarни tuzatди, lekin **suhbat o'rtасидаги qisqa javoblar**
hali engine tomonidан ushlanadi.

## Ildiz (aniqlangan)

`service.build_response()`:
```python
res = engine.handle(message, ...)        # ← HAR xabarда, BIRINCHI
if res.get('intent') != 'unknown':
    return res                           # agent ishlamaydi
```

Faol vazifa (`AgentTask`) faqat `_try_agent` ichida, KEYIN yuklanadi. Ya'ni
bron davom etayotган bo'lsa ham, «soch olish» (harakat so'zisiz, lekin `soch`
= barber toifasi) engine tomonidан ushlaб qolinadi → agent soya qilinadi →
suhbat uziladi.

Qisqa javoblar buni doim keltirib chiqaradi: «soch olish», «11 da», «birinchi»,
«ha» — vazifa ichида ma'noli, lekin engine ularни mustaqil so'rov deб talqin
qiladi.

## Yechim — faol vazifa bo'lsa engine'ni CHETLAB O'T

`build_response()` boshida, `engine.handle()` DAN OLDIN:

```python
# Faol (yarim qolgan) bron/buyurtma vazifasi bor bo'lsa — suhbatni AGENT
# egallaydi. Engine qisqa javoblarni («soch olish», «11 da») mustaqil so'rov
# deb talqin qilib, oqimni uzmasligi uchun uni butunlay chetlab o'tamiz.
if request is not None and not _is_anonymous(request):
    if _has_active_task(request):
        agent_res = _try_agent(message, history, location, request, voice)
        if agent_res is not None:
            return _as_agent_response(agent_res)
        # agent ishlamasa — pastga tushib engine bilan davom etamiz (zaxira)
```

### `_has_active_task(request)` yordamchisi
`AgentTask` da shu foydalanuvchi uchun `status='active'` va muddati o'tmagan
vazifa bormi — shuni tekshiradi. `task.active_task()` mantiqини qayta ishlat
(dublikat qilma). Bitta indekslangan so'rov — arzon.

### `_as_agent_response(agent_res)` yordamchisi
46-55-qatorlardagi agent-javob yig'ish mantiqини funksiyaga chiqar (dublikat
bo'lmasin) — ham yangi yo'l, ham eski yo'l ishlatsin.

⚠️ **Muhim nuanslar:**
- Faqat **kirgan** foydalanuvchi (anonimда agent o'chiq — o'zgarmaydi)
- Agent `None` qaytarsa (LLM ishlamadi) — engine'ga tushib, uzilmasin (zaxira)
- Vazifa tugagach (`status != active`) — keyingi xabar yana engine fast-path'ga
  tushadi (oddiy so'rovlar bepul qolsin)

## Nega bu to'g'ri arxitektura
Vazifa davomida foydalanuvchi «eng yaqin dorixona» deб mavzu almashtirса ham,
agent buni hal qila oladi (uning `places` tool'i bor) — ya'ni engine'ни
chetlab o'tish hech narsa yo'qotmaydi. Vazifa ichида agent to'liq ega.

## Testlar
- Faol booking `AgentTask` bor + «soch olish» → agent chaqiriladi, engine
  MANZIL qaytarmaydi (mock LLM bilan)
- Faol vazifa bor + «11 da» → agent (engine emas)
- Faol vazifa YO'Q + «eng yaqin dorixona» → engine fast-path (o'zgarmaydi)
- Vazifa `status='done'` bo'lsa → engine yana ishlaydi
- Anonim + faol vazifa (bo'lishi mumkin emas, lekin) → engine, agent o'chiq

## Jonli tasdiq (kvota bo'lsa) — TO'LIQ ZANJIR
Bu topshiriqning butun maqsadi — 5 navbat uzilmasдан:
```
«sartaroshxonadan joy bron qil»  → xizmat so'raydi
«soch olish»                      → vaqt so'raydi   ← HOZIR SHU UZILYAPTI
«11 da»                           → tasdiq kartаси (30 000)
[Tasdiqlash]                      → «bron qilindi»
```
Har navbatни yoz. Uzilса — qayerда, nega.

## Chegara
- Engine fast-path'ни vazifasiz holatда o'zgartirma (bepul so'rovlar qolsin)
- Arxitektura o'zgarishи shu — lekin u PROMPT_10 ning aniq talabi, boshqa
  o'zgarish qilma
- `python manage.py test assistant` — hammasi o'tsin (hozir 333)

`git commit` qilma. Nima ishlamаганини halol ayt. Ortiqcha maqtov kerak emas.
