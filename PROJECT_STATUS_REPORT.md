# SamCity — Loyiha holati hisoboti (to'liq audit)

> Sana: 2026-07-13 · Metod: kod bazasi auditi (Django 12 app + Flutter), URL
> xaritasi, admin panel, management buyruqlar, TODO qidiruvi, vizionni
> (README / LOYIHA_QOLLANMA / ROLLAR_TAHLILI) joriy kod bilan taqqoslash.
> Bu hisobot faqat tahlil — hech qanday kod o'zgartirilmagan.

---

## 1. Umumiy xulosa

Platforma **9 ta yirik modul** bo'yicha web (Django templates) + mobil (Flutter)
paritetida ishlaydi va yaqinda katalog integratsiyasi (Phase 1–5 + frontend
tuzatishlar, commit `0aa8da4`) yakunlangan. Kod sifati yaxshi: 121 test o'tadi,
`flutter analyze` toza, xavfsizlik auditi o'tgan, i18n (uz/ru/en) 207 ta satr
to'liq tarjima qilingan.

**Launch'ni to'xtatib turgan 3 ta tizimli to'siq (ROLLAR_TAHLILI bilan bir xil,
hali ham dolzarb):**

1. **SMS provayder ulanmagan** — `.env`da `SMS_BACKEND=console` (OTP konsolga
   chiqadi). Eskiz/Playmobile backend kodi tayyor (`sms/backends.py`), faqat
   haqiqiy hisob ma'lumotlari kerak.
2. **Payme/Click jonli emas** — webhook kodi TO'LIQ yozilgan
   (`payments/payme.py` — JSON-RPC 6 metod; `payments/click.py` —
   Prepare/Complete, imzo tekshiruvi bilan), lekin `.env`da merchant kalitlari
   bo'sh. Shu sababga bog'liq: e'lon boost, xizmat to'lovi, taksi to'lovi,
   bron oldindan to'lovi — hammasi hozircha simulyatsiya.
3. **FCM push yo'q (mobil tomonda)** — backend tayyor (`notifications/push.py`
   firebase-admin bilan, `DeviceToken` modeli, `/api/notifications/device/`),
   lekin Flutter `pubspec.yaml`da firebase_messaging **umuman yo'q** — token
   yuboradigan hech kim yo'q. Kuryer/taksist/do'kon egasi ilova yopiqda
   buyurtmani ko'rmaydi.

---

## 2. To'liq amalga oshirilgan funksiyalar (modul kesimida)

### main — foydalanuvchi, e'lonlar, mahalla, jamiyat
- Telefon+OTP ro'yxatdan o'tish/kirish (web+mobil), JWT (mobil), remember-me
- E'lonlar (Ad): 7 kategoriya, 10 tagacha rasm, xarita, ko'rish/kontakt statistikasi
- E'lon amallar: sevimli, shikoyat (AdReport), savol (AdInquiry), sotildi belgisi
- Boost rejalar (7/30/90 kun) — *lekin to'lovsiz, 5-bo'limga qarang*
- Global qidiruv + autocomplete, saqlangan e'lonlar
- Mahalla: e'lonlar, murojaat/shikoyat (status bilan), so'rovnoma (poll+ovoz+izoh)
- Hokim paneli + tuman e'loni (web+mobil)
- Yordam so'rovlari (community help) + ko'ngilli bo'lish
- Ish e'lonlari (JobAd) + rezyume (ResumeAd), yopish/ishga joylashdim statuslari
- Kommunal to'lov yozuvlari (utility_*)
- Profil, boshqaruv paneli (dashboard), ochiq profil, reyting
- APK yuklab olish sahifasi (`/app/` + `main/static/samcity.apk`)
- 3 tilli i18n: infratuzilma + 207 satr uz/ru/en to'liq tarjima
- Reklama kampaniyasi «Hammaga yuborish» (AdCampaign, admin-only)

### delivery — do'konlar, katalog, buyurtma
- Do'kon turlari: `delivery` (supermarket) va `mahalla`; do'kon ochish arizasi
  (StoreRequest) + rais/admin tasdig'i (web UI bor)
- **Markaziy katalog (yangi, to'liq):** 153 mahsulot (122+ rasm), qidiruv,
  kategoriya/birlik/brend filtrlari (web+mobil+API), rasm preview, katalogdan
  mahsulot yaratish (nom/tavsif prefill), mahalla 10-limit (custom) +
  cheksiz katalog, X/10 hisoblagichlar, «Katalog»+birlik badge'lari,
  rasm fallback (do'kon rasmi → katalog rasmi) web/mobil/API'da
- Savat (3 bo'lim: e'lon/yetkazish/mahalla), nomli savatlar, checkout
- Buyurtma holat mashinasi + real-time kuzatuv (WebSocket), pickup tasdig'i
- Kuryer: ro'yxatdan o'tish, dashboard, buyurtma olish/qo'yish, joylashuv uzatish, reyting
- Do'kon egasi paneli: buyurtmalar, mahsulot CRUD, e'lon (StoreUpdate), obunachilar
- Mijoz↔do'kon chati (web+mobil)
- CLI: `import_catalog` (--validate-only bilan), `export_catalog`,
  `catalog_health`, seed buyruqlari

### taxi
- Xizmatlar, taksistlar, marshrutlar (A→B), mashina, safar (Trip)
- Real-time haydovchi joylashuvi (WebSocket), yaqin haydovchilar, narx baholash
- Taksist ro'yxati/boshqaruvi, reyting/sharh (xizmat + taksist)
- To'lov yozuvi — *simulyatsiya (5-bo'lim)*

### booking
- Joylar (Venue) CRUD, xizmatlar, xodimlar, slot tizimi
- Bron + oldindan to'lov (escrow mantiq) + no-show jarima + bekor qilish
- Egasi paneli (manage_bookings), mijoz bronlarim — web+mobil

### places / xarita
- Joylar, sharh, sevimli, GeoJSON, mahallalar chegarasi, marshrut, reverse-geocode
- Turizm/mebel/elektronika ro'yxatlari; OSM + Carto zaxira tile

### payments
- Provider/ServicePayment/Transaction modellari, kvitansiya, to'lovlarim
- Payme JSON-RPC webhook (6 metod, atomic+select_for_update)
- Click Prepare/Complete (MD5 imzo) — *ikkalasi ham kalit kutmoqda*

### notifications
- Real-time WebSocket bildirishnoma (web qo'ng'iroqcha + mobil)
- Backend FCM push (`push.py`) — *mobil klient yo'q (1-bo'lim)*

### sms / telegrambot
- SMS abstraksiyasi: eskiz/playmobile/console backendlar tayyor
- Telegram OTP bot (dev/demo kanal) — token sozlangan, ishlaydi

### api (mobil REST)
- Barcha modullar uchun JWT'li API + OpenAPI/Swagger (`/api/docs/`)
- Health/ready/seed-status endpointlar (deploy monitoring)

### mobile (Flutter)
- 16 feature moduli: auth/OTP, e'lonlar(+yaratish), ish, taksi, delivery
  (savat/buyurtma/egasi paneli/katalog picker paginatsiya bilan), bron,
  mahalla (panel), hokim, community, xarita, to'lov, bildirishnoma, profil,
  do'kon chati — Riverpod + go_router + dio + secure storage

---

## 3. Qisman amalga oshirilgan / tugallanmagan funksiyalar

| # | Funksiya | Holat | Dalil |
|---|----------|-------|-------|
| 1 | **Onlayn to'lov (jonli)** | ⚠️ Kod tayyor, kalitlar yo'q | `.env`: `PAYME_*`/`CLICK_*` bo'sh |
| 2 | **SMS OTP (jonli)** | ⚠️ Backend tayyor, provayder hisobi yo'q | `.env`: `SMS_BACKEND=console` |
| 3 | **FCM push** | ⚠️ Server tayyor, Flutter klienti YO'Q | `mobile/pubspec.yaml`da firebase yo'q |
| 4 | **E'lon boost to'lovi** | ⚠️ To'lovsiz "active" bo'ladi (demo) | `main/views.py:1634` — BoostPayment to'g'ridan yaratiladi |
| 5 | **Taksi to'lovi** | ⚠️ Karta simulyatsiya | `taxi/models.py:367` izoh |
| 6 | **Xizmat to'lovi (ServicePayment)** | ⚠️ Demo (karta oxirgi 4 raqami) | `payments/models.py:70` |
| 7 | **Parolni tiklash (web)** | ❌ "Tez orada" deb turibdi | `login.html:788` |
| 8 | **Ish arizasi (application) tizimi** | ❌ Faqat telefon-kontakt | ROLLAR §3–4; kodda Application modeli yo'q |
| 9 | **Saqlangan qidiruv + ogohlantirish** | ❌ Yo'q | SearchQuery yig'iladi, foydalanuvchi funksiyasi yo'q |
| 10 | **Taksi avtomatik dispatch** | ❌ "Yaqin haydovchiga taklif" yo'q | ROLLAR §5; kodda dispatch mantiqi yo'q |
| 11 | **Ko'p xodimli do'kon (chat/boshqaruv)** | ❌ Faqat egasi | TODO: `delivery/chat.py:8`, `delivery/models.py:779` |
| 12 | **Mobil offline rejim / force-update** | ❌ Yo'q | ROLLAR mobil baho |
| 13 | **Mobil i18n / yorug' tema** | ❌ Bitta til (uz), qorong'i tema | mobile/lib — hardcoded matnlar |
| 14 | **Kuryer daromad hisoboti** | ❌ Yo'q | ROLLAR §9 |
| 15 | **Do'kon egasi analitikasi (savdo)** | ❌ Buyurtma ro'yxatidan boshqa yo'q | ROLLAR §8, §12 |
| 16 | **Savat bayrog'i nomuvofiqligi** | ⚠️ Mahsulot detalida faqat env flag, do'kon sahifasida pickup ham hisobga olinadi | `delivery/views.py:110` vs `:133` |
| 17 | iOS build (App Store talablari) | ⚠️ Sozlamalar bor, push/sign-in tekshirilmagan; native yuklab olish yo'q (dizayn bo'yicha) | `mobile/ios/` |

## 4. Yashirin TODO / FIXME / "keyinroq" belgilar

Kod bazasida rasmiy `TODO/FIXME` juda kam (toza saqlangan). Topilganlari:

| Joy | Matn |
|-----|------|
| `delivery/chat.py:8` | TODO (keyingi bosqich): ko'p xodimli do'kon — hozircha faqat egasi javob beradi |
| `delivery/models.py:779` | TODO (keyingi bosqich): ko'p xodimli do'kon |
| `payments/models.py:71` | "Payme/Click keyinroq ulanadi" (ServicePayment demo) |
| `taxi/models.py:367` | "TO'LOV (karta — simulyatsiya, Payme/Click keyinroq ulanadi)" |
| `main/templates/registration/login.html:788` | "Parolni unutdim?" — «Tez orada qo'shiladi» |
| `main/templates/community/mahalla_home.html:150` | "Tez orada bu yerda mahallalar ro'yxati chiqadi" (bo'sh holat) |

Flutter'da TODO yo'q (faqat bo'sh-holat matnlari).

## 5. Admin-only / CLI-only — web yoki mobil UI'ga chiqarilmagan

| Funksiya | Qayerda | UI'ga chiqarish istiqboli |
|----------|---------|---------------------------|
| **Katalog hisoboti** (statistika + rasmi yo'qlar ro'yxati) | `delivery/admin.py:159` report_view | Do'kon egasiga kerak emas; superadmin uchun joyida |
| **Rasmi yo'q mahsulotlar CSV eksporti** | `delivery/admin.py:171` | Admin-only, joyida |
| **`promote_to_catalog`** — do'kon mahsulotini katalogga ko'chirish | `delivery/admin.py:76` action | Kelajakda egasi "katalogga taklif qilish" tugmasi bo'lishi mumkin |
| **AdCampaign «Hammaga yuborish»** | `main/admin.py:237` send_campaigns | Atayin admin-only (reklama) |
| **SearchQuery statistikasi** — nima qidirilyapti | `main/admin.py:28` | ROLLAR §1 bo'yicha sotuvchilarga trend sifatida ochish g'oyasi bor |
| **AdReport moderatsiyasi** | `main/admin.py:22` | Admin-only, joyida |
| **HelpRequest moderatsiyasi** | `main/admin.py:59` | Admin-only |
| **DistrictAdmin / ChatAdmin (rais) tayinlash** | `main/admin.py:194, 331` | Rol tayinlash admin-only; rais paneli web'da bor |
| **OTP kodlar ko'rinishi** | `main/admin.py:98` | Faqat debug |
| CLI: `catalog_health`, `export_catalog`, `import_catalog`, `check_media`, `check_boosts`, seed'lar | management/commands | Server operatsiyalari, UI shart emas |

## 6. Vizion ↔ joriy holat (gap-hisobot)

LOYIHA_QOLLANMA vizioni bo'yicha modul-modul:

### ✅ To'liq amalga oshirilgan
- E'lonlar bozori (kategoriya, rasm, xarita, statistika, moderatsiya)
- Mahalla moduli (e'lon, murojaat, so'rovnoma, yordam, hokim paneli) — chat
  Phase 1'da **ataylab olib tashlangan** (vizion o'zgargan, qoldiq kod yo'q)
- Delivery + **markaziy katalog** (10-limit biznes qoidasi bilan) — eng so'nggi
  bosqichda yakunlangan, web/mobil/API paritet
- Booking (slot, escrow, jarima) — professional daraja
- Taksi (marshrut, real-time, reyting) — dispatch'siz
- Xarita/joylar, ish/rezyume, bildirishnoma (WebSocket), 3 tilli web i18n
- Xavfsizlik bazasi (audit, throttle, webhook qulflari), Docker/Render deploy,
  OpenAPI hujjat, health-check, testlar (121)

### ⚠️ Qisman (kod bor, jonli emas yoki yarim)
- To'lovlar: webhook kodi tayyor ↔ merchant kalitlari yo'q; boost/taksi/xizmat
  to'lovlari simulyatsiya rejimida
- OTP: console/Telegram rejimda ↔ Eskiz hisobi yo'q
- Push: server tayyor ↔ Flutter klient yo'q
- Mobil: paritet bor, lekin bitta til, offline yo'q, push yo'q
- Kuryer/egasi uchun push'siz real-time faqat ilova ochiqda

### ❌ Amalga oshirilmagan (vizion/ROLLAR'da bor, kodda yo'q)
- Ish arizasi tizimi (bir tugmali apply + nomzodlar ro'yxati)
- Saqlangan qidiruv + "yangi e'lon" ogohlantirishi
- Taksi avtomatik dispatch (yaqin haydovchiga taklif)
- Kuryer daromad hisoboti, do'kon savdo analitikasi
- Narx tarixi, sotuvchi reytingi e'lon kartasida, ichki xaridor-sotuvchi chat
- Telefon raqamni yashirish/proksi qo'ng'iroq
- Parolni tiklash oqimi

## 7. Repo tozaligi (yo'l-yo'lakay kuzatuvlar)

- `posts/` — app emas, 2 ta adashib qolgan rasm fayli (o'chirsa bo'ladi)
- `mobile app/` — bo'sh papka; `New/`, `python` fayl — qoldiqlar
- Seed userlar telefoni `+998...` formatda — web login 9 xonali kutadi
  (demo hisoblar web'dan kira olmaydi; auditda 1 tasi tuzatilgan)
- `db.sqlite3` repo'da — dev uchun qulay, lekin prod PostgreSQL

## 8. Tavsiya etilgan ustuvorlik (keyingi ish uchun)

1. **Jonli infratuzilma** (kod yozilmaydi, sozlanadi): Eskiz hisobi + Payme/Click
   merchant kalitlari + Firebase loyihasi
2. **Flutter FCM klienti** — firebase_messaging + token ro'yxati (backend tayyor)
3. **Boost'ni haqiqiy to'lovga ulash** — Payme/Click jonli bo'lgach eng tez daromad
4. Parol tiklash (OTP orqali) — kichik ish, katta UX yutuq
5. Ish arizasi tizimi — ROLLAR bo'yicha eng katta funksional bo'shliq
6. Kuryer/egasi analitika panellari

---
*Hisobot auditga asoslangan; kod o'zgartirilmagan. Manba hujjatlar: README.md,
LOYIHA_QOLLANMA.md, ROLLAR_TAHLILI.md (388 qator, rol-rol tahlil), DEPLOY.md.*
