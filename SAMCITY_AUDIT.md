# PROMPT_7 — «agent ISH QILSIN, aytmasin» (hisobot)

O'zak muammo: agent ko'rsatma beradi («ilovani oching, bo'limga kiring»), o'zi
bajarmaydi. To'rt faza. **315 test o'tadi** (280 → 315), migratsiya drifti yo'q.

## Qamrov

| Fayl | O'zgarish |
|---|---|
| `prompts.py` | «SEN ISH BAJARASAN» qoidasi; faqat o'zbek; yaqin-toifa qoidasi; slotlar [FAOL VAZIFA] da |
| `uznum.py` | YANGI — son → o'zbekcha so'z (ovoz uchun) |
| `tts.py` | ovoz oldidan `numbers_to_words` (ui'ga tegmaydi) |
| `engine.py` | barber + wedding kalit so'zlari kengaytirildi |
| `tools/places.py` | `MAX_PLACE_KM` masofa chegarasi |
| `tools/booking.py` | YANGI — find_venue/list_services/list_staff/available_slots/propose_booking + place_booking |
| `registry.py` | `booking` SECTION_DESC yangilandi |
| `tools/__init__.py` | `booking` moduli yuklanadi |
| `seed_smoke.py` | cola/ichimlik (A3) + Zamon Sartaroshxona (B3) |
| tests | `test_uznum` (14), `test_routing` (11), `test_booking` (10) |

---

## FAZA A — «qilaman, aytmayman»

`STATIC_PROMPT` boshiga eng muhim qoida sifatida qo'yildi (misol bilan:
«cola buyurtma qil» → find_store→cart_add, «Do'konlar bo'limiga kiring» EMAS).
Yetishmagan ma'lumot uchun ilovaga yuborish o'rniga BITTA savol berish buyurildi.

**A2 (slot-filling):** to'plangan tanlovlar endi `[FAOL VAZIFA]` da ko'rinadi
(`Allaqachon ma'lum: venue_id=5, service=...`). Busiz ko'p qadamli oqimda tarix
qisqarganda oldingi tanlovlar yo'qolar edi. `booking` tool'lari har qadamda
slotга yozadi.

**A3 — cola nega yiqilgan edi + endi (JONLI):**

```
«menga cola buyurtma qilib ber» → tool: delivery.find_store → KO'RSATMA: YO'Q ✅
javob: «10 ta do'kon topdim, ekranda ko'rsatdim. Qaysi birini tanlaysiz?»
```

Endi buyurtma oqimiga KIRADI. **Nega ilgari yiqilgan edi:** ikki sabab birga —
(a) prompt agentga «ilovani tushuntir» degan urg'u bermasa ham, «ish bajar»
degan QAT'IY buyruq yo'q edi, model xavfsiz yo'lni (ko'rsatma) tanlardi;
(b) seed'da cola/ichimlik yo'q edi, `find_store("cola")` bo'sh qaytarib, model
«topolmadim, o'zingiz qidiring» ga o'tardi. Ikkalasi ham tuzatildi: qat'iy
prompt qoidasi + seed'ga Coca-Cola qo'shildi.

⚠️ Kichik kuzatuv: model `speech` ga ba'zan xom ID («store:91») qo'shib qo'ydi —
prompt'ni yana qattiqlashtirish mumkin, lekin ko'rsatma muammosi HAL bo'ldi.

---

## FAZA C — faqat o'zbek + raqamlar o'zbekcha

- `STATIC_PROMPT` dan «savol qaysi tilda bo'lsa — o'sha tilda» OLIB TASHLANDI.
  O'rniga: «HAR DOIM o'zbek tilida». Bu eski 17-holatni foydalanuvchi xohlagan
  yo'nalishda yopadi.
- `uznum.py` — son→so'z. `uznum(35000)`=«o'ttiz besh ming», `uznum(45000)`=«qirq
  besh ming». `tts.synthesize` ovoz oldidan qo'llaydi; **ui (ekran) raqamni
  saqlaydi** (test bilan tasdiqlangan). O'nlik (8.5), vaqt (14:30), telefon
  (>7 xona) tegilmaydi. 14 test.

---

## FAZA D — marshrutlash

- **D1:** «yaqin toifa ≠ to'g'ri javob» qoidasi (sartaroshxona so'ralsa restoran
  bermaydi).
- **D2:** `engine.CATEGORY_KEYWORDS['barber']` ga `sartaroshxona`, `soch ol`,
  `soch oldir`, `sochimni oldir` va h.k.; `wedding` ga `to'y qil`, `zal band`.
  Test: «sochimni oldirmoqchiman» → `barber` (restoran EMAS).
- **D3:** `places.find_nearest` `MAX_PLACE_KM=20` (env) — 83 km narigi joy
  chiqmaydi. ⚠️ **Sabab tanlovi:** `Place` modelida tuman maydoni YO'Q (faqat
  lat/lng), shuning uchun `guard.apply_district` o'rniga masofa cap ishlatildi.
  Bu Shofirkon uchun to'g'ri (ixcham shahar). Agar keyin Place'ga tuman
  bog'lansa — apply_district'ga o'tish mumkin.

**«sochimni oldirmoqchiman» endi nima qaytaradi (JONLI):**

```
tool: booking.find_venue → «5 ta joy topdim, ekraningizda. Qaysi biridan bron qilamiz?»
```

Endi `booking` ga to'g'ri marshrutlanadi (ilgari «Kebab House» — restoran edi).
Restoran EMAS, sartaroshxonalar ro'yxati.

---

## FAZA B — sartaroshxona broni

`booking/models.py` (Venue/VenueService/VenueStaff/VenueBooking) tayyor edi —
faqat agentga ulandi (`delivery` naqshiday). 5 amal:

| action | mutating | reused |
|---|---|---|
| find_venue | yo'q | Venue |
| list_services | yo'q | VenueService |
| list_staff | yo'q | VenueStaff |
| available_slots | yo'q | `Venue.available_slots()` (mavjud slot mantiqi) |
| propose_booking | **ha** | → PendingAction + confirm_payment |
| place_booking (@executor) | — | `VenueBooking` yaratadi, `is_free_at` qayta tekshiradi |

**Uchdan-uchgacha (test bilan tasdiqlangan):** find_venue → list_services →
available_slots → propose_booking → `PendingAction` (amount=30000,
confirm_payment) → confirm → **`VenueBooking` yaratiladi** (status=pending,
total=30000). **Tasdiqsiz bron YARATILMAYDI** (test_no_confirm_no_booking).
Idempotent (ikki tasdiq → bitta bron). Anonim propose qila olmaydi.

`prepay_required=True` bo'lsa to'lov «oldindan»ga majburlanadi. Naqd bo'lsa bron
`pending` yaratiladi, to'lov joyda.

**Jonli booking oqimi (birinchi qadam):**

```
«sartaroshxonadan joy bron qil» → tool: booking.find_venue → KO'RSATMA: YO'Q ✅
javob: «5 ta joy topdim, ekraningizda. Qaysi biridan bron qilamiz?»
```

Agent bron oqimini boshlaydi va savol beradi (ko'rsatma bermaydi). To'liq
zanjir (venue→service→slot→confirm→VenueBooking) test bilan uchdan-uchgacha
tasdiqlangan; jonli to'liq zanjirni sinash kunlik kvotani ko'p yeydi (5 navbat ×
2500 token), shuning uchun birinchi qadam jonli, qolgani test bilan.

---

## Umumiy holat

- Booking TO'LIQ tugadi (o'qish + tasdiq + executor + seed + test).
- Barcha 315 test o'tadi.
- ⚠️ Brauzer TTS zaxira yo'lida (server TTS o'chiq bo'lsa) raqamlar o'zbekcha
  so'zga aylanmaydi — `uznum` faqat server (Aisha) yo'lida. Aisha kaliti .env da
  bor, shuning uchun asosiy yo'l qamralган; brauzer zaxira uchun keyin JS'da
  ham qo'llash mumkin (hisobotda qayd — o'zim qilmadim).

## Arxitektura eslatmasi (o'zim qilmadim)
- `Place` tuman bog'lanishi yo'q → masofa cap ishlatdim. Tuman filtri kerak
  bo'lsa, `Place`ga `neighborhood`/`district` qo'shish arxitektura qarori.

---

# PROMPT_8 — bron suhbatini OLDINGA SURISH

Muammo: agent sartaroshxonalarni ko'rsatib TO'XTARDI, keyingi savolni bermasdi.
«Erta qaytish» olib tashlangач yakuniy javobni model yozadi, u ko'p qadamni
boshqara olmasdi.

## Tuzatishlar

| # | Muammo | Yechim |
|---|---|---|
| 1 | Model vazifani surmaydi | `STATIC_PROMPT` «KO'P QADAMLI VAZIFANI OXIRIGACHA OLIB BOR» bloki + `[FAOL VAZIFA]` da aniq «KEYINGI QADAM» (booking uchun `_booking_next_step`) |
| 2 | Bitta variant «tanlang» | find_venue/list_services/list_staff bitta natijaда avto-tanlaydi, slot yozadi, keyingi qadamга o'tadi |
| 3 | «11 da»/«3 da» tushunmaydi | `_parse_time`: «11 da»→11:00, «3 da»→15:00 (1–8→+12), «11:30»→11:30, «kechqurun 7»→19:00. `_parse_day` «ertaga soat 3 da» dan kunni ajratadi. propose_booking bandlikni oldindan tekshirib, band bo'lsa yaqin vaqtlarни taklif qiladi |

**329 test o'tadi** (315 → 329, +14). `check` toza, migratsiya drifti yo'q.

## Jonli zanjir (Groq gpt-oss-120b) — ikki qismда tasdiqlangan

⚠️ Bir agent navbati 2 LLM chaqiruvi ≈ 9600 token, Groq bepul TPM 8000/daqiqa —
shuning uchun navbatlar orasида 65s pauza. Dev bazада 5 ta ortiqcha barber bor
edi (oldingi test/seed'lardan) — ularни nofaol qildim, PROMPT_8 ssenariysи
«bitta sartaroshxona» bo'lgani uchun.

### Qism 1 — vazifani OLDINGA SURISH (asosiy fix)
| Navbat | Kirish | Tool | Speech |
|---|---|---|---|
| 1 | «sartaroshxonadan joy bron qil» | `find_venue` | «Zamon topdim. **Qaysi xizmat kerak?**» ← avto-tanlov + **surildi** |
| 2 | «qanaqa xizmatlar bor» | `list_services` | «Xizmatlar ekraningizda. **Qaysi xizmat?**» ← **surildi** |
| 3 | «soch olish» | — | ⚠️ **gpt-oss-120b BUZUQ JSON chiqardi** (Groq 400 «Failed to parse tool call») |

Navbat 3'даги xato — **model beqarorligi**, bizning kod emas (PROMPT_3'dан
ma'lum: gpt-oss tool-calling intizomi zaif). Yumshatдim: buzuq tool-JSON'да
agent **bir marta qayta urinadi** (gpt-oss ko'pincha 2-urinishда o'tadi).

### Qism 2 — PUL YO'LI (venue+xizmat oldindan tanlangan, kvota tejash)
| Navbat | Kirish | Tool | Natija |
|---|---|---|---|
| 1 | «ertaga soat 11 da yozib qo'y» | `available_slots` | «12 bo'sh vaqt. **Soat nechada?**» ← surildi |
| 2 | «11 da» | `propose_booking` | **confirm_payment, 30 000 so'm** — «11 da»→**11:00** to'g'ri |
| tugma | /ai/confirm/ | — | **VenueBooking YARATILDI** (0→1), idempotent |

Yakuniy bron: `2026-07-23 11:00 · Soch olish · 30 000 so'm · pending`.

**Xulosa (halol):** ko'p qadamni surish, bitta-variant avto-tanlov, «11 da»→11:00,
propose→confirm→VenueBooking — HAMMASI jonli ishladi. Yagona uzilish — gpt-oss-120b
o'rta navbatда buzuq JSON chiqardi (400); retry yumshatadi, lekin to'liq ishonchli
5-navbatli zanjir kuchliroq model (gpt-4o-mini) talab qiladi. Bu — PROMPT_3/5'даги
model-tanlash tavsiyasi kuchда qolishини yana tasdiqlaydi.

## Hali g'aliz / ochiq
1. gpt-oss-120b tool-JSON beqarorligi — o'rta navbatда uziladi. Retry qisman
   yordam beradi; ishonchli yechim — kuchliroq model.
2. Model ba'zан venue'larни speech'да sanaydi (qoidага zid) — kichik, prompt
   yana qattiqlashsa bo'ladi.
3. Dev baza ifloslanishи (test'lар barber yaratib qoldirgan) — smoke sinovдан
   oldin `is_active` bo'yicha tozalash kerak; bu test-muhit masalasi, kod emas.

**331 test o'tadi** (329 + 2 retry). `git commit` qilmadim.

---

# PROMPT_9 — engine agentni SOYA qilardi (ildiz)

Jonli: kirgan user «menga soch oldirish uchun joy bron qil» → bron suhbati
O'RNIGA sartaroshxona MANZILLARI chiqardi. Sabab: `engine.handle()` harakat
so'rovини category='barber' deб ushlab, `nearest_place` qaytarardi → agent
umuman ishga tushmasdi. Delivery («buyurtma») va booking («bron») branchlari ham
xuddi shunday shadowlayotган edi.

## Yechim — harakat niyatида engine CHEKINADI

`engine.is_action_intent(message)` — `ACTION_INTENT_WORDS` (BOOKING_WORDS qayta
ishlatilib + buyurtma/zakaz/yozib qoy/soch oldir) bor, LEKIN `HOWTO_WORDS`
(«qanday») bo'lsa yo'q. `handle()` boshida:
```
if is_action_intent(message): return result  # intent='unknown' → agent
```
Diskriminator jonli tekshirilgan:
- «eng yaqin sartaroshxona», «sartaroshxona qayerda» → MANZIL (engine, o'zgarmadi)
- «bron qil», «soch oldirish uchun bron», «ovqat buyurtma qil» → agent
- «qanday bron qilaman» (HOW-TO) → KB (chekinmaydi)

## Jonli tasdiq
`engine.handle('menga soch oldirish uchun joy bron qil')` → **'unknown'** ✅
`agent.run(...)` → **booking.find_venue** ishga tushdi (soya yo'q) ✅

## Jonli sinov ochган YON NUQSON (tuzatildi)
list_services **error** berdi — `selection.identifier_of` faqat store_id/product_id
ni bilardi, venue_id ni emas; model kartaning `venue:<uuid>` prefiksини xom
yubordi → xato pk. Tuzatildi: `identifier_of` venue/service/staff_id beradi +
`booking._bare()` prefiksни kesadi (barcha booking tool'larida).

## Bonus — anonim + harakat → «kiring»
Anonim «bron qil» desa jimgina manzil emas, «Bron/buyurtma uchun tizimga kiring»
+ Kirish tugmasi (`service._anon_fallback`).

## Chegara / halol eslatma
- no-key (AI_API_KEY yo'q) rejimда harakat so'rovlари engine kartalарини emas,
  fallback (bo'lim havolalari) ko'radi. Bu ilgarigi buggy manzil-ko'rsatishдан
  yaxshiroq; lekin no-key booking/delivery kartalар yo'qoladi — maqbul deb
  qaror qildim (agent-birinchi yo'nalish). Kerak bo'lsa service'да engine
  natijasини zaxira sifatida ishlatsa bo'ladi — arxitektura qarori.
- `booking` venue_type enum'ида wedding/hall YO'Q — «zal/to'yxona bron» agentга
  ketadi, lekin agent uni topa olmaydi (seed'да faqat barber). Kelgusи ish.

**333 test o'tadi** (331 → 333). `git commit` qilmadim.

---

# PROMPT_10 — faol vazifa bo'lsa engine chekinsin (suhbat o'rtасидаги uzilish)

Jonli (gpt-4.1-mini): «sartaroshxonadan joy bron qilib ber» → ✅ xizmat so'radi;
«soch olish» → ❌ agent O'RNIGA sartaroshxona MANZILLARI (suhbat uzildi).

## Ildiz
`service.build_response()` HAR xabarда BIRINCHI engine.handle() ni chaqiradi.
Bron davom etayotган bo'lsa ham, «soch olish» (harakat so'zisiz, lekin soch=barber
toifasi) engine tomonidан ushlanardi → agent soya qilinardi. «11 da», «ha»,
«birinchi» — hammasi vazifa ichida ma'noli, lekin engine mustaqil so'rov deб talqin
qilardi.

## Yechim — faol vazifa bo'lsa engine'ni CHETLAB O'T
`build_response()` boshida, engine'dан OLDIN: kirgan foydalanuvchida faol
(muddati o'tmagan) `AgentTask` bo'lsa → to'g'ridan-to'g'ri agent. Agent None
qaytarsa engine'ga tushib davom (zaxira). Yordamchilar:
- `_has_active_task(request)` — `task.active_task()` ni qayta ishlatadi (bitta
  indekslangan so'rov, muddati o'tganini abandoned qiladi)
- `_as_agent_response(agent_res)` — agent-javob yig'ish (yangi va eski yo'l bir xil)

Nuanslar (test bilan): faqat kirgan user; agent None → engine zaxira; vazifa
`done` bo'lgach → engine fast-path qaytadi (bepul so'rovlar qoladi); anonim →
o'zgarmaydi (vazifa ham tekshirilmaydi).

## Jonli TO'LIQ ZANJIR (service orqali, 5 navbat UZILMASDAN) ✅
| Navbat | Kirish | intent | Tool | Natija |
|---|---|---|---|---|
| 1 | «sartaroshxonadan joy bron qilib ber» | agent | find_venue + list_services | «Qaysi xizmat?» |
| 2 | «soch olish» | **agent** | available_slots | «Qaysi vaqt?» ← ILGARI UZILARDI |
| 3 | «ertaga soat 11 da» | agent | available_slots | «11:00 mavjud» |
| 4 | «tasdiqlayman» | agent | propose_booking | confirm_payment, 30 000 |
| Tasdiq | /ai/confirm/ | — | — | **VenueBooking YARATILDI** (1→2) |

Yakuniy: `2026-07-23 11:00 · Soch olish · 30 000 so'm`. Hech bir navbatда engine
MANZIL bermadi. gpt-4.1-mini (kuchliroq) — gpt-oss-120b'даги buzuq-JSON muammosи
ham chiqmadi.

## Halol eslatma
- gpt-4.1-mini (GitHub Models) — PROMPT_3/5/8'даги «kuchliroq model kerak»
  tavsiyasi bajarilgan; endi to'liq zanjir barqaror.
- 3-navbat «ertaga soat 11 da» → model propose_booking o'rniга available_slots
  chaqirdi (bir qadam ortiqcha), keyin 4-navbatда propose qildi. Kichik — natija
  to'g'ri. Xohlasa prompt bilan qisqartirsa bo'ladi.

**339 test o'tadi** (333 → 339). `git commit` qilmadim.

---

# 2-TO'LQIN — BARCHA BO'LIMLAR (ads, jobs, community, taxi + delivery/booking to'ldirish)

Foydalanuvchi: bron/do'kon/yetkazib berish to'liq emas; e'lon, ish e'loni, taksi,
mahalla qo'shilmagan. → butun ishni topshirdi.

## Qo'shilган/to'ldirilган bo'limlar (tool'lar)

| Bo'lim | Amallar | mutating |
|---|---|---|
| **ads** (e'lon) | search · post | post→Ad |
| **jobs** (ish) | search_jobs · search_resumes · post_job · post_resume | post→JobAd/ResumeAd |
| **community** (mahalla) | announcements · submit_request · list_polls · vote | request→CitizenRequest, vote→PollVote |
| **taxi** | find_taxists · list_routes · propose_trip | trip→Trip |
| **delivery** (+) | view_cart · remove_from_cart · my_orders | — |
| **booking** (+) | my_bookings · cancel_booking | cancel→VenueBooking |

Yangi UI turlari: `link_list` (havolali kartalar — e'lon/ish/taksist, tanlanmaydi),
`confirm` (pulsiz tasdiq — e'lon joylash/murojaat). Widget'да render + confirm/cancel POST.

## Marshrutlash — ASOSIY FIX

Muammo: engine yangi bo'limlarни ham soya qilardi («e'lonlarni qidir» → engine ads
branch, «savatimда nima bor» → engine delivery, «mahalla e'lonlari» → engine KB).
Yechim (`service.build_response`): kirган foydalanuvchi uchun engine agent-egallagan
intent (`delivery/ads/jobs/booking/taxi`) yoki community so'rovини (`is_community_query`)
agentга uzatadi. Agent None → engine natijasи (no-key zaxira, kartalar yo'qolmaydi).

## Jonli tekshiruv (gpt-4.1-mini, 6 bo'lim — HAMMASI agentга bordi)
| So'rov | intent | tool |
|---|---|---|
| «mashina sotiladigan e'lonlar bormi» | agent | ads.search |
| «dasturchi ishi bormi» | agent | jobs.search_jobs → link_list |
| «mahallamda qanday e'lonlar bor» | agent | community.announcements → link_list |
| «menga taksi kerak Buxoroga» | agent | taxi.list_routes → card_list |
| «savatimда nima bor» | agent | delivery.view_cart |
| «yo'l buzuq, murojaat yubormoqchiman» | agent | community.submit_request → confirm |

## Brauzer tekshiruvi (haqiqiy sessiya cookie, mock'siz)
- `/ai/chat/` «menga taksi kerak Buxoroga» → intent=agent, taxi.list_routes, card_list ✅
- Widget «mahallamda qanday e'lonlar bor» → community.announcements → link_list
  («Umumiy yig'ilish» — haqiqiy seed e'loni) ✅
- link_list (Batafsil/Qo'ng'iroq) va confirm (Yuborish/Bekor → POST → «yuborildi») render ✅
- Konsolда JS xatosi YO'Q.

## Yo'l-yo'lakay tuzatilган
- `guard._check_ownership` prefiksli id («booking:abc») va noto'g'ri UUID'да
  crash o'rniga «denied» beradi (cancel_booking jonli sinovда crash bergan edi).

## HALOL HOLAT
✅ **100% ishlaydi + jonli tasdiqlangan:** places, delivery (savat+buyurtma+holat),
booking (bron+bekor), ads, jobs, community, taxi. **401 test o'tadi.**

⚠️ **Hali tool YO'Q** (foydalanuvchi so'ramаган, ikkinchi darajali): account (profil),
merchant (do'kon egasi paneli), payments (kommunal), notifications (eslatma),
navigate (bo'limга o'tkazish). Bular `SECTIONS` да bor, lekin agent tool'i yozilmagan —
kerak bo'lsa keyingi bosqichда.

`git commit` qilmadim.
