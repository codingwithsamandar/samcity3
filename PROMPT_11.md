# Claude Code uchun topshiriq — taksi + boshqa joylar seed, ish tajriba filtri, + tekshiruv

Foydalanuvchi jonli sinovда uch narsани so'radi. Diagnostika qilinган: ikковi
**seed ma'lumotи yo'qligидан**, funksiyalar allaqачон yozилган.

⚠️ **Avval:** men (arxitektor) test ishga tushira olmasдан to'g'ridan-to'g'ri
3 ta tool qo'shдим — ularни ham TEKSHIR (pastда, 0-qadam).

---

## 0-qadam — mening testсиз qo'shган tool'larимни tekshir

`assistant/tools/delivery.py` va `assistant/tools/jobs.py` ga men qo'lда
qo'shдim (test yugurtмасдан):

- `delivery.clear_cart` — savatни butunlай tozalaydi
- `jobs.my_resumes` — foydalanuvchining o'z rezyumelari
- `jobs.my_jobs` — foydalanuvchining o'z vakansiyalари

Bularни ko'zдан kechир: registry'ga to'g'ri ro'yxatga tushдими, model
maydonlари to'g'rimи (`ResumeAd`, `JobAd`, `Cart`), `link_list`/`ui` to'g'ri
ishlаtилганmи. Kerak bo'lsa tuzаt. Har biriga test yoz. `python manage.py test
assistant` o'tsин.

---

## 1. Taksi ishlаmаyaptи — seed ma'lumotи yo'q

`assistant/tools/taxi.py` (find_taxists, list_routes, propose_trip) tayyor,
lekin bazада faol `Taxist`/`Route` yo'q → bo'sh natijа.

`assistant/management/commands/seed_smoke.py` ga taksi ma'lumotini qo'sh
(mavjud `taxi/management/commands/seed_taxi.py` ni namunа qil, model
maydonlарини o'zинг tekshir):

- 3-4 ta `Taxist` (Shofirkon), `is_active=True`, ba'zиси `is_online=True`,
  `full_name`, `phone`, `car_model`, `trips_count`
- Har taksistga 2-3 ta `Route` (`point_a`→`point_b`, `passenger_price`),
  masalan «Shofirkon → Buxoro», «Shofirkon → Bozor», `is_active=True`
- Idempotent (qayta ishlаtилса dublikat yaratмасин)

Tekshir: seed'дан keyin «menga taksi kerak» / «Buxoroга taksi» → find_taxists /
list_routes natijа qaйtaradi.

## 2. Faqat sartaroshxona bron bo'lyaptи — boshqa joy turlari uchun seed

`booking.py` `VENUE_TYPE_ENUM = ['barber', 'beauty', 'restaurant', 'cafe']` —
kod to'rttаsини qo'llаb-quvvatlaydi, lekin seed'да faqat barber bor.

`seed_smoke.py` ga qo'sh (mavjud «Zamon Sartaroshxona» naqshиday):

- 1 ta `beauty` (go'zallик saloni) — «Malika Go'zallik Saloni», 2 xizmat
  (soch turmagi, manikюр), 2 usta
- 1 ta `restaurant` — «Osh Markazi», 2 xizmat/stol (masalan «2 kishilik stol»,
  «4 kishilik stol»), 1 usta yoki stol
- Har birида `working_hours_start/end`, `prepay_required=False`,
  `VenueService` (name, price, duration_minutes), `VenueStaff`
- Idempotent

Tekshir: «go'zallik salonига yozil» / «restoranда stol bron qil» → booking oqим
boshlanади (barber bilan bir xil).

⚠️ **To'yxona (wedding) — BU TOPSHIRIQДА EMAS.** U kunlик/sig'им bo'yicha
bron (slot emas) — `Venue.price_per_day`, `capacity`. Boshqача propose oqим
kerak. Alohида, keйingi topshiriq. Hozир faqat slot-turlar (beauty/restaurant/
cafe).

## 3. Ish tajribаси bo'yicha qidirish

`jobs.search_resumes` faqat matn (title/skills/about/location) bo'yicha
qidiradi. Tajriba darajаси filtri yo'q.

- `ResumeAd` (va `JobAd`) `experience` maydonи choices'ini tekshir
  (`get_experience_display` ishlаtилган — demak choices bor)
- `search_resumes` ga ixtiyoriy `experience` parametri qo'sh (`enum` choices
  bilan), berilса filtrlasин
- Foydalanuvchi tabiiy tilда aytса («3 yillik tajribали», «katta tajribали»)
  — buni choice'ga map qil (kichик yordamchи yoki prompt tavsifи)
- `search_jobs` ga ham xuddi shундай (agar `JobAd` da tajriba talabi bo'lsa)

Tekshir: «5 yildan ko'p tajribали dasturchи» → tajriba filtri qo'llanади.

---

## Bajarish tartibi
1. 0-qadam (mening tool'larимни tekshir + test)
2. Taksi seed (1)
3. Boshqa venue seed (2)
4. Tajriba filtri (3)
5. `python manage.py test assistant` — hammasи o'tsин (hozир ~333 + yangilar)
6. `python manage.py seed_smoke` — xatosиz o'tsин
7. Kvota bo'lsa jonли: «taksi kerak», «restoranда stol bron», «5 yil tajribали
   dasturchи» — natijа qaйtardими

## Hisobotда kerak
1. 0-qadam: mening 3 tool'ımда xato bormidi, tuzаtилдими
2. Taksi endi ishlаydими (seed + jonли)
3. Boshqa joy turlари bron bo'lyaptими
4. Tajriba filtri ishlаydими
5. Nima hali ishlаmади

## Chegара
- To'yxona (wedding) date-bron — QILMA, keйingi topshiriq
- Seed'ni idempotent qil, mavjud «Zamon Sartaroshxona»ни buzма
- `git commit` qilma. Nima ishlаmаганини halol ayt.
