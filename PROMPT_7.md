# Claude Code uchun topshiriq (QAYTA YOZILGAN) — agent ISH QILSIN, aytmasin

Foydalanuvchi widget'ni haqiqatan sinab, uchta jiddiy kamchilik topdi. Ular
bitta o'zakka borib taqaladi: **agent nima qilishni AYTADI, lekin o'zi
QILMAYDI.** Bu — butun loyihaning mag'zi. Bu topshiriq shuni tuzatadi.

Jonli misollar (screenshot bilan tasdiqlangan):
- «menga cola buyurtma qilib ber» → agent: «men bevosita buyurtma bera
  olmayman. Ilovani ochib: 1. Do'konlar bo'limi 2. cola deб yozing 3. Savatga
  qo'shish...» ← ⛔ agent'da `cart_add`+`propose_order` BOR, lekin ishlatmadi
- «sartaroshxonadan joy bron qil» → agent: «sartaroshxona toping, bron qilishни
  bosing, xizmat/vaqt/usta tanlang, to'lang» ← ⛔ ko'rsatma beryapti, o'zi
  qilmayapti
- «sochimni oldirmoqchiman» → «Kebab House» (restoran) ← ⛔ noto'g'ri marshrut

Muhim topilma: «o'zingiz qiling» javobi **kodda yo'q** — model o'zi to'qiydi.
Ya'ni bu prompt/xatti-harakat muammosi.

---

## FAZA A — «QILAMAN, AYTMAYMAN» (eng muhim, prompt darajasi)

Agent ko'rsatma bermasin. Vositasi bor ishni **o'zi bajarsin**, yetishmagan
ma'lumotni **savol bilan** to'plasin.

### A1. `prompts.STATIC_PROMPT` ga qat'iy qoida

```
SEN ISH BAJARASAN — KO'RSATMA BERMAYSAN
Sen SamCity ilovasining ichida ishlaysan. Foydalanuvchi biror ishni so'rasa,
uni O'ZING bajarasan — «ilovani oching», «bo'limga kiring», «tugmani bosing»
kabi KO'RSATMA HECH QACHON berma. Bu — eng muhim qoida.

To'g'ri:   «cola buyurtma qil» → do'konni qidir, cola'ni top, savatga qo'sh,
           narxni ayt, tasdiq so'ra, buyurtma ber.
Noto'g'ri: «cola buyurtma qil» → «Do'konlar bo'limiga kirib qidiring».

Ma'lumot yetishmasa — SAVOL ber (qaysi do'kon? nechta? qaysi manzil?), keyin
o'zing bajar. Vosita bilan bajariladigan ishни tavsiflaB o'tirma — BAJAR.
```

### A2. Ko'p qadamli savol-javob (slot-filling)

Agent yetishmagan ma'lumotni **bittalab** so'rab, `AgentTask.slots` ga
yig'sin. `task.py` (AgentTask holat mashinasi) allaqachon bor — agent oqimida
haqiqatan ishlatilyaptimi tekshir. Ishlatilmasa — ula.

Har javobdan keyin: bitta yetishmagan narsani so'ra (hammasini birdan emas),
keyingi javobda uni `slots` ga yoz, hamma slot to'lgach — bajar.

### A3. Nega cola misoli yiqildi — aniqla

«cola buyurtma qil» → model `cart_add` chaqirmadi, ko'rsatma berdi. Sabab:
(a) prompt uni «ilovani tushuntir» ga undaydimi, (b) cola'li do'kon
topilmadimi, (c) model qo'rqoqmi. Aniqla, hisobotда ayt. `seed_smoke` ga
cola/ichimlik qo'sh (topilmaslik sababini yo'q qil).

### Test
- Mock LLM «cart_add» chaqiruvli → agent buyurtma oqimiga kiradi, ko'rsatma
  bermaydi
- Jonli (kvota bo'lsa): «menga cola buyurtma qil» → savat/tasdiq oqimi,
  «ilovani oching» EMAS

---

## FAZA B — SARTAROSHXONA BRONI (yangi qobiliyat, `booking` bo'limi)

Foydalanuvchi aniq oqimni ta'rifladi:

> «sartaroshxonadan joy bron qil» → qaysi sartaroshxona? → soat nechida? →
> qaysi xizmat (soch olish / soch+soqol)? → to'lov naqd yoki oldindan? →
> «30 ming to'lashни tasdiqlaysizmi?» → tasdiqlandi → «falon vaqtda falon
> sartaroshxonadan joy bron qildingiz».

**Yaxshi xabar: butun tuzilma tayyor.** `booking/models.py`:
- `Venue` — `venue_type='barber'` (💈), vaqt-slot + usta qo'llab-quvvatlaydi
  (`SLOT_TYPES` da bor), `prepay_required`, `working_hours_start/end`
- `VenueService` — xizmat + narx (soch olish, soch+soqol)
- `VenueStaff` — usta (sartarosh)
- `VenueBooking` — bron yozuvi
- Slot mantiqi: `Venue._day_bookings_by_staff`, `venue_slots` view'i bor

Faqat **agent'ga ulash** kerak — `delivery` naqshiday.

### B1. `assistant/tools/booking.py` yarat

`delivery.py` ni namuna qil. Amallar:

| action | Nima | mutating |
|---|---|---|
| `find_venue` | joy topish (`venue_type` filtri: barber, beauty, restaurant) | yo'q |
| `list_services` | xizmatlar + narx | yo'q |
| `list_staff` | ustalar | yo'q |
| `available_slots` | berilgan kun/xizmat uchun bo'sh vaqtlar | yo'q |
| `propose_booking` | ✱ bron tasdiqqa | **ha** |

`propose_booking` → `PendingAction` + `confirm_payment` UI (xizmat, usta, vaqt,
narx, to'lov usuli). `@executor` tasdiqdan keyin `VenueBooking` yaratadi.
Mavjud `booking` view/mantiq (`booking/views.py`, `venue_slots`, `booking_pay`)
ni QAYTA ISHLAT — dublikat qilma.

### B2. Slot-filling oqimi (`AgentTask`, goal='service_booking')

Yetishmagan slotlar tartibi: `venue → service → staff → time → payment_method`.
Har birини bittalab so'ra. Hammasi to'lgach `propose_booking`.

To'lov usuli: `Venue.prepay_required` bo'lsa «oldindan», aks holda «naqd yoki
oldindan» so'ra. Naqd bo'lsa — bron yaratiladi, to'lov joyda. Oldindan bo'lsa —
to'lov oqimiga (mavjud `booking_pay`) ulanadi yoki hozircha `PendingAction`
summasi ko'rsatiladi.

### B3. `booking` bo'limini `registry.SECTIONS` da yoqib, seed qo'sh

`seed_smoke.py` (yoki yangi `seed_booking_smoke`) ga:
- 1 ta sartaroshxona: «Zamon Sartaroshxona», `venue_type='barber'`, Shofirkon,
  ish vaqti 09:00–20:00, `prepay_required=False`
- 2 ta xizmat: «Soch olish» 30 000, «Soch + soqol» 45 000
- 2 ta usta: «Aziz aka», «Bekzod»
- Idempotent

### Test
- To'liq oqim (mock LLM): find_venue → list_services → available_slots →
  propose_booking → PendingAction (amount=30000, confirm_payment UI) →
  confirm → VenueBooking yaratiladi
- Tasdiqlanmasa — VenueBooking YARATILMAYDI (arxitektura himoyasi)

---

## FAZA C — FAQAT O'ZBEK TILI + RAQAMLAR O'ZBEKCHA

Foydalanuvchi: «hozircha faqat o'zbek tilida yaxshi gapirsin, raqamlarni ruscha
aytyapti».

### C1. Prompt — faqat o'zbekcha

`STATIC_PROMPT` da «foydalanuvchi tilida javob ber» bo'lsa — OLIB TASHLA.
O'rniga:

```
TIL: HAR DOIM o'zbek tilida (lotin) javob ber, savol qaysi tilda bo'lishidan
qat'i nazar. Boshqa tillar keyinroq qo'shiladi.
```

Bu eski 17-holatni (ruscha savol) foydalanuvchi xohlagan yo'nalishда yopadi.

### C2. Raqamlarni o'zbekcha so'z bilan (ovoz uchun)

Ruscha raqam muammosi: TTS «35000» ni raqam sifatida o'qiydi. Yechim —
`speech` matnida raqamlarni **o'zbekcha so'z** qil: «35 000 so'm» → «o'ttiz besh
ming so'm».

- Kichik yordamchi yoz: `assistant/uznum.py` — son → o'zbekcha so'z
  (0–9 999 999 yetadi: birlar, o'nlar, yuz, ming, million)
- Faqat `speech` (ovoz) matnida qo'llan — `ui` (ekran) da raqam RAQAM qolsin
- Aisha kaliti endi `.env` da bor — server qayta ishga tushgach o'zbek ovozi
  ishlaydi; bu yordamchi raqamlar ham o'zbekcha eshitilishini kafolatlaydi

### Test
- `uznum(35000)` → «o'ttiz besh ming»
- `uznum(30000)` → «o'ttiz ming», `uznum(45000)` → «qirq besh ming»
- speech'da «45 000 so'm» → «qirq besh ming so'm»; ui'da «45 000» qoladi

---

## FAZA D — MARSHRUTLASH TUZATISHLARI

### D1. Almashtirmaslik (sartaroshxona ≠ restoran)

`STATIC_PROMPT` ga:
```
YAQIN TOIFA ≠ TO'G'RI JAVOB. Sartaroshxona so'ralsa restoran BERMA. Mos
tool bo'lmasa rostini ayt, boshqa narsa O'YLAB TOPMA.
```
(Endi `booking` ulangач, sartaroshxona MOS tool oladi — bu qoida boshqa
ulanmagan bo'limlar uchun himoya bo'lib qoladi.)

### D2. `barber` kalit so'zlari (engine.py)

`CATEGORY_KEYWORDS['barber']` ga tabiiy shakllar: `'soch ol'`, `'soch kes'`,
`'soch qildir'`, `'sartaroshxona'`. `wedding` ni ham kengaytir: `'to'y qil'`,
`'zal band'`, `'to'yxona kerak'`.

### D3. Tuman/masofa filtri (`places`)

`places.find_nearest` `ctx.district` bo'yicha filtrlasin (`guard.apply_district`)
YOKI masofa chegarasi (`MAX_PLACE_KM=20`, env). 83 km natija chiqmasin.
`Place` tuman bog'lanishini tekshir, qaysi biri to'g'ri ekanini hisobotда ayt.

---

## Bajarish tartibi (MUHIM)

Fazalar katta. Shu tartibda, har fazadan keyin test:

1. **FAZA A** (prompt + slot-filling) — eng arzon, eng katta ta'sir
2. **FAZA C** (o'zbek + raqam) — arzon, mustaqil
3. **FAZA D** (marshrutlash) — arzon
4. **FAZA B** (booking) — eng katta ish, oxirida

Agar B ni bir seansda toza tugatib bo'lmasa — A/C/D + booking O'QISH tool'larини
(find_venue, list_services, available_slots) tugat, `propose_booking` va
seed'ни keyingi seansга qoldir. Yarim ishlangan booking'ni qoldirma.

## Har fazadan keyin
- Faqat tegilgan modul testini yugurt (tez), to'liq to'plamни FAZA oxirida
- `python manage.py test assistant` — oxirida hammasi o'tsin (hozir 280)

## Hisobotда kerak
1. FAZA A: «cola buyurtma qil» endi buyurtma oqimiga kiradimi (jonli, kvota
   bo'lsa). Cola nega yiqilgan edi (A3)
2. FAZA B: sartaroshxona broni uchdan-uchgacha ishladimi (find→service→slot→
   confirm→VenueBooking). Tasdiqsiz bron yaratilmasligi tasdiqlandimi
3. FAZA C: raqamlar o'zbekcha eshitiladimi (uznum testlari)
4. FAZA D: «sochimni oldirmoqchiman» endi nima qaytaradi
5. Booking to'liq tugadimi yoki qisman (halol ayt)
6. Umumiy ball o'zgarishi (kvota bo'lsa smoke)

## Chegara
- Faqat o'zbek tili (boshqa tillar EMAS — foydalanuvchi shuni so'radi)
- Demo ma'lumotни o'chirma
- Arxitektura o'zgarishи bo'lsa — hisobotда ayt, o'zing qilma

`git commit` qilma. Ortiqcha maqtov kerak emas — nima ishlamadi, shuni ayt.
