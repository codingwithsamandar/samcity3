# Claude Code uchun topshiriq — engine agentni soya qilyapti (bron/buyurtma yo'li uzilgan)

Jonli sinov (kirgan foydalanuvchi, brauzer orqали tasdiqlangan): «menga soch
oldirish uchun joy bron qil» → agent bron suhbati O'RNIGA sartaroshxona
MANZILLARI chiqdi. Agent umuman ishga tushmadi.

## Ildiz (aniqlangan)

`service.build_response()`:
```python
res = engine.handle(message, ...)
if res.get('intent') != 'unknown':
    return res            # ← engine javob berса, agent ISHLAMAYDI
```

`engine.handle()` (~608-630):
```python
category = detect_category(qn)   # "soch oldirish"/"sartarosh" → 'barber'
...
if category:
    ...return nearest_place...   # intent='nearest_place' → agent shadowlandi
```

PROMPT_7 D2 da `barber` kalitlari engine'ga qo'shildi («sartaroshxona qayerda»
uchun). Yon ta'sir: endi **bron/buyurtma** so'rovlari ham category topib, engine
tomonidан ushlanadi — agent (booking/delivery) ishlamaydi.

Xuddi shu muammo `restaurant` + «ovqat buyurtma» da ham bor (restoran manzili
chiqadi, delivery agenti emas).

## Yechim — harakat niyatи bo'lsa engine chekinsin

`engine.handle()` da, `if category:` bloki BAJARILISHIDAN OLDIN:

```python
# Harakat niyati (bron/buyurtma/yozib qo'y) — bu JOY TOPISH emas, AMAL.
# Engine chekinadi (intent='unknown' qoladi), agent (booking/delivery) hal qiladi.
if category and _contains_any(qn, ACTION_INTENT_WORDS):
    return result   # intent 'unknown' → service.build_response agentga uzatadi
```

`ACTION_INTENT_WORDS` — yangi ro'yxat (mavjud `BOOKING_WORDS`, `DELIVERY_WORDS`
ni qayta ishlat + kengaytir):

```
bron, bron qil, band qil, joy bron, yozib qo'y, yozib qoy, yoziб ber,
buyurtma, buyurtma qil, zakaz, order,
soch oldir, soch oldirish, sartaroshga yozil
```

⚠️ **Diskriminator aniq bo'lsin:**
- «eng yaqin sartaroshxona», «sartaroshxona qayerda» → harakat yo'q → engine
  MANZIL beradi (o'zgarmaydi)
- «sartaroshxonadan joy bron qil», «soch oldirish uchun yozib qo'y» → harakat
  bor → engine chekinadi → agent bron suhbati

## Muhim tekshiruv — "bron" so'zи NEGA e'tiborsiz qolgan

`engine` da `BOOKING_WORDS` allaqachon bor (`['bron', 'band qil', ...]`), lekin
`handle()` da category tekshiruvidан OLDIN ishlatilmaydi. Ehtimol pastroqда
booking uchun alohida branch bor — uni ko'r. Agar engine o'zi «bron» ni boshqa
javobga yo'naltirsa, u ham agentни soya qilishi mumkin. Butun `handle()` oqimини
ko'zdан kechir: `category` dан tashqari qaysи branchlar `intent != 'unknown'`
qaytaradi va bron/buyurtma so'rovини noto'g'ri ushlaydi.

## Testlar
- `engine.handle('menga soch oldirish uchun joy bron qil')` → `intent='unknown'`
  (agentga uzatiladi)
- `engine.handle('sartaroshxonadan joy bron qil')` → `intent='unknown'`
- `engine.handle('eng yaqin sartaroshxona')` → `intent='nearest_place'`,
  category='barber' (manzil — o'zgarmaydi)
- `engine.handle('restorandan ovqat buyurtma qil')` → `intent='unknown'`
- `engine.handle('eng yaqin restoran')` → `intent='nearest_place'` (manzil)
- `service.build_response(...)` bilan integratsiya: kirgan user + «bron qil» →
  agent chaqiriladi (mock LLM bilan tasdiqla)

## Jonli tasdiq (kvota bo'lsa)
Kirgan holда «menga soch oldirish uchun joy bron qil» → agent bron suhbati
boshlanadi («qaysi xizmat?»), MANZIL kartаси EMAS.

## Bonus (agar oson bo'lsa) — mehmonga «kiring» deyish
Oldingi topilma: anonim foydalanuvchi «bron qil» desa, jimgina manzil chiqadi.
Endi engine chekinса, anonim uchun agent ham ishlamaydi (o'chirilgan) →
`engine.fallback` yoki `service` da anonim + harakat niyati → muloyim
«Bron/buyurtma uchun tizimga kiring» javobи. Katta ish bo'lsa — alohida
qoldir, hisobotда ayt.

## Chegara
- `barber`/`restaurant` kalitlарини engine'dан OLIB TASHLAMA — «qayerda»
  so'rovlари uchun kerak. Faqat harakat niyatида chekin.
- Arxitektura o'zgarishи bo'lsa — hisobotда ayt, o'zing qilma

`python manage.py test assistant` — hammasi o'tsin (hozir 331). `git commit`
qilma. Nima ishlamaganини halol ayt.
