# Claude Code uchun topshiriq — to'liq QA sweep: 15 rol, routing, kamchiliklar, tuzatish

Foydalanuvchi «15 rol sifatida sinaб, HAMMA xatoni top va tuzat» dedi. Arxitektor
(men) jonli sinадi, lekin GitHub bepul limiti (15/daqiqa) jonli testни
ishonchsiz qildi (429 fallback ≠ bug). Shuning uchun bu topshiriq — **test
suite + paced smoke_agent** bilan to'liq sweep.

## 0. Arxitektor to'g'ridan-to'g'ri qilган o'zgаришlarни tekshir

Men (test yugurtмасдан) quyidagilarни o'zgartirдim — TEKSHIR + test yoz:

- `engine.py` `ACTION_INTENT_WORDS` ga delivery iboralari qo'shildi:
  `'yetkazib ber', 'yetkaz', 'olib kel', 'olib keling'`.
  Maqsad: «somsa yetkazib bering» → agent (engine KB emas). Tekshir:
  `engine.is_action_intent('somsa yetkazib bering')` → True;
  `engine.is_action_intent('yetkazib berish qanday ishlaydi')` → False (HOW-TO).
- `delivery.clear_cart`, `jobs.my_resumes`, `jobs.my_jobs` (oldingi seansда
  qo'shган — agar hali test bo'lmasa, test yoz).

`python manage.py test assistant` — hammasi o'tsин.

## 1. Routing sweep — natural iboralar to'g'ri yo'nalyaptиmi

Har bo'lim uchun, foydalanuvchи TABIIY aytadigan iboralarни sana va
`engine.handle()` + `service.build_response()` to'g'ri yo'naltиrаyaptиmи tekshir
(agent kerak bo'lganда engine/KB SOYA qilмаsин):

- **delivery:** «lavash yetkazib bering», «somsa olib keling», «ovqat buyurtma
  qil», «suv olib kel» → agent (find_store/order)
- **taxi:** «taksi chaqir», «mashina kerak», «Buxoroga borishim kerak» → agent
- **booking:** «soch oldiraman», «stol bron qil», «salonga yozil» → agent
- **ads:** «mashinamni sotaman», «e'lon joylash» → agent; «mashina sotib
  olmoqchiman» → agent (search)
- **jobs:** «ish kerak», «dasturchi kerak», «xodim kerak» → agent
- **account:** «buyurtmalarim», «bronlarim», «profilim» → agent (2-bo'lim)
- **community:** «shikoyat yozmoqchiman», «so'rovnoma» → agent

Har biri uchun: engine SOYA qilса (KB/category/fallback), `ACTION_INTENT_WORDS`
ga qo'sh yoki KB entry'ни action niyatида chekintir. `knowledge.py` KB
entry'lari action so'rovларини ushlаб qolmasин.

⚠️ HOW-TO istisnо saqlansин: «qanday buyurtma qilaman» → KB (agent emas).

## 2. Yetishmayotgan `account` bo'limi — YANGI `tools/account.py`

Foydalanuvchи o'zига tegишli narsalarни so'rайди, hozир agent «o'zингиз
qiling» deб ko'rsатма beryapti. `SECTIONS` da `account` bor (registry), lekin
tool yo'q. `delivery.my_orders` naqshиday yoz:

- `my_orders` (delivery'да bor — account'ga ham ulash yoki shунга yo'naltir)
- `my_bookings` — foydalanuvchи bronlari (`VenueBooking.filter(user=...)`)
- `my_trips` — taksi safarlari (`Trip.filter(passenger=...)`)
- `my_ads` — e'lonlari (`Ad.filter(user=...)`)
- `profile` — profil ma'lumotини ko'rsatadi (ism, telefon, mahalla)
- `change_name` (mutating? — o'z profilи, past xavf; tasdiq bilan) — ismни
  o'zgartиради. ⚠️ Foydalanuvchи yozувига tegади — ehtiyot, faqat `ctx.user`
  ning O'Z profilи, `guard` orqали.

«ismимни Samandarga o'zgartir» → `change_name` → tasdiq → yangилайди.
«bronlarim» → `my_bookings`. «buyurtmalarim» → `my_orders`.

## 3. Jobs/ads «u haqida» — selection ulash

`jobs.search_jobs/search_resumes` va `ads.*` qidiruvи `link_list` ishlаtади —
`SelectionSet` yo'q, shuning uchun «u haqида to'liq ma'lumot» ishlаmайди.

- Qidiruvni `card_list` + `sel.create()` ga o'tkaz (delivery/booking naqshиday)
- `job_details` / `resume_details` / `ad_details` action qo'sh — selection'дан
  yechади («u haqида», «birinchiси», «Django backend»)

## 4. Ads «bekor qil» oqими

«bekor qil» → «qanday amalni?» → «e'lon qo'shishni» → «sarlavhани ayting» —
chalkаш. `ads.py` ni ko'rib, bekor qilish oqимини aniqлаштиr yoki mavjud
e'lonlарни ko'rsатиб tanlatib bekor qildir.

## 5. 15 rol — paced smoke_agent

`smoke_agent` (yoki yangi `qa_personas`) buyrug'ига 15 rol qo'sh, HAR so'rov
orasида pauza (GitHub 15/daqiqa — kamida 5s, 429'да kutиб qayta urин).
Rollar (tabiiy til, xato-yozувlар bilan):

1. Och odam: «qornim ochdi, somsa yetkazib bering»
2. Bosh og'rig'и: «boshim og'riyapti, dorixona kerak»
3. Ish beruvchи: «5 yildan ko'p tajribали dasturchi kerak»
4. Ish izlоvчи: «menga ish kerak, haydovchiман»
5. Sartarosh mijozи: «ertaga soch oldirаман, joy bron qil»
6. To'y egаси: «to'yxona kerak, 200 kishi» (wedding — 6-bo'lim)
7. Yo'lovchи: «Buxoroga borишim kerak»
8. Restoran mijozи: «kechga 4 kishiga stol bron qil»
9. Sotuvchи: «mashinамни sotaman, Nexia 2015»
10. Xaridor: «arzon telefon bormi»
11. Mahalla fuqаrоси: «suv yo'q, shikoyat yozmoqchiman»
12. Profil: «ismимни Samandarga o'zgartir»
13. Tarix: «buyurtмаларимни ko'rsat»
14. Follow-up: [qidiruvдан keyin] «u haqида batafsil»
15. Chalkаш: «bekor qil» (kontekstsиз)

Har rol uchun yoz: qaysi tool, to'g'ri yo'naldими, xato bo'lса — sabab
(routing / model / ma'lumot yo'q / kod).

## 6. Wedding (to'yxona) — kunlик bron

`booking` hozир slot-based (barber/salon/restoran). To'yxona — kunlик, sig'им
(`Venue.price_per_day`, `capacity`). `find_venue` ga `wedding`/`hall` venue_type
qo'sh, va kунlик bron oqими (`propose_booking` ga sana + kishi soni variantи).
Seed: 1-2 to'yxona. Bu eng katta qism — oxirида qil, vaqt yetмаса hisobotда ayt.

## Tartib
1. 0 (arxitektor o'zgаришlari + test)
2. 1 (routing sweep)
3. 2 (account)
4. 3 (selection)
5. 4 (ads bekor)
6. 5 (15 rol smoke — kvота yetgаnicha)
7. 6 (wedding — vaqt bo'lsa)
8. `python manage.py test assistant` — hammаси o'tsин

## Hisobotда
1. Har fazада nima tuzatildi
2. 15 rol natijаси (jadval: rol → tool → ✅/❌ → sabab)
3. Kvота yetмаган rollар (halol ayt)
4. Wedding qilindими yoki qoldи
5. Umumiy test soni

`git commit` qilma. Ortiqcha maqtov kerak emas — nima ishlаmади, shuni ayt.
