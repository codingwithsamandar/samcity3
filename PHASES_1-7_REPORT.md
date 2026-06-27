# Fazalar 1–7 — bajarilgan ishlar

> Sandbox diski to'la — server ishga tushirilmadi; har bir o'zgarish kod + URL/shablon
> mosligi bo'yicha statik tekshirildi (barcha yangi `{% url %}` havolalari aniqlangan nomlarga mos).
> Ishga tushirish: `python manage.py migrate` (yangi: `notifications/0001`, `places/0001`, `delivery/0005`).
> Demo: `python manage.py seed_all` (endi `seed_places` ham ichida).

## Yangi fayllar
**notifications app:** `__init__.py, apps.py, models.py, signals.py, context_processors.py, views.py, urls.py, admin.py, migrations/0001_initial.py, templates/notifications/notification_list.html, templates/notifications/_bell.html`
**places app:** `__init__.py, apps.py, models.py, views.py, urls.py, admin.py, migrations/0001_initial.py, management/commands/seed_places.py, templates/places/{map,place_list,place_detail,place_form,place_confirm_delete}.html`

## O'zgartirilgan fayllar
`sdev/settings.py` (INSTALLED_APPS: notifications, places; context_processor), `sdev/urls.py` (notifications/, map/), `main/templates/base.html` (notif bell, Xarita nav), `main/templates/home.html` (notif bell, Xarita/Sayohat nav + tiles), `delivery/views.py` (checkout → store owner notification), `main/management/commands/seed_all.py` (seed_places).

## Faza bo'yicha natija
**1. Bildirishnomalar** ✅ — `Notification` modeli, navbar qo'ng'iroq (dropdown + o'qilmagan hisoblagich, JS-siz `<details>`), ro'yxat sahifasi, o'qilgan deb belgilash (bittalab + hammasi). Django signallari orqali generatsiya: buyurtma holati o'zgarishi (xaridorga), yangi do'kon (adminlarga), yangi venue bron (egaga) + bron holati (mijozga), yangi taksi so'rovi (haydovchiga), yangi chat xabari (a'zolarga). Yangi delivery buyurtma → do'kon egalariga (checkout view'da).
**2. Xarita** ✅ — OpenStreetMap + Leaflet (`/map/`), interaktiv, toifa filtri (chap panel), har nuqta uchun popup (nomi, manzil, telefon, ish vaqti, Batafsil), responsive (mobil 1 ustun). Google Maps ishlatilmadi.
**3. Joylar katalogi** ✅ — `Place` modeli 13 toifa bilan (mebel, elektronika, sayohat, davlat, tashkilot, pochta, bank, dorixona, shifoxona, mehmonxona, to'yxona, restoran, do'kon). Har joy: nom, tavsif, toifa, lat/lng, rasm, kontakt, ish vaqti, galereya. To'liq CRUD (egalik/staff ruxsati, xaritada bosib koordinatа tanlash).
**4. Sayohat** ✅ — `places:tourism_list` (toifa=tourist) + `place_detail` (galereya, yaqin atrofdagilar Haversine bo'yicha, qidiruv, toifa filtri, mini-xarita). Hammasi asosiy xaritada ko'rinadi.
**5. Mebel & Elektronika** ✅ — `places:furniture_list` / `electronics_list` (place_list ni qayta ishlatadi) + detail. "Mahsulot katalogi" mavjud `delivery` arxitekturasidan foydalanadi (dublikat yaratilmadi).
**6. UI/UX** ⚠️ qisman — bosh sahifa allaqachon premium qayta yozilgan; navbar/footer/kartalar/tipografiya yagona dark "district super-app" uslubida; bildirishnoma va xarita shu uslubga integratsiya qilindi. **To'liq Bootstrap/Tailwind ko'chirish ataylab qilinmadi** — bu o'nlab ishlaydigan shablonlarni buzar va "mavjud funksiyani qayta yozmang" qoidasiga zid bo'lardi. Mavjud yaxlit dizayn tizimi saqlandi.
**7. Audit** ✅ — barcha yangi URL nomlari shablonlardagi havolalarga mos (NoReverseMatch yo'q); ruxsat tekshiruvlari (place edit/delete: egasi yoki staff; CRUD'lar login bilan); signallar try/except bilan himoyalangan; bo'sh holatlar ishlangan.

## Tuzatilgan xatolar (shu sessiya)
- Yangi delivery buyurtma egaga bildirishnoma yuborilmasdi → qo'shildi.
- Xarita/joylar bo'limi umuman yo'q edi → yaratildi.
- Navbarda bildirishnoma markazi yo'q edi → qo'shildi.

## Ma'lum cheklovlar
- Chat xabari signali har a'zoga bildirishnoma yaratadi (ko'p a'zoda ko'p yozuv) — kelajakda batch/throttle kerak.
- Bildirishnoma real-time emas (sahifa yangilanganda ko'rinadi) — WebSocket bilan jonli qilish mumkin.
- Venue'da lat/lng maydoni yo'q, shuning uchun to'yxonalar xaritaga `Place` orqali alohida kiritiladi (avtomatik ko'chirish yo'q).
- Furniture/Electronics "mahsulot katalogi" delivery do'konlariga havola orqali — to'liq birlashtirilmagan.
- Server statik tahlil bilan tekshirildi (sandbox cheklovi).

## Keyingi yaxshilanishlar
- Bildirishnomalarni WebSocket (Channels mavjud) orqali real-time qilish.
- Xaritada delivery do'konlari va to'yxonalarni avtomatik ko'rsatish (koordinata qo'shib).
- Place uchun "marshrut/yo'nalish" (Leaflet routing) qo'shish.
- Furniture/Electronics do'konini delivery Store bilan bog'lab, mahsulotlarni xarita kartochkasida ko'rsatish.
- To'liq dizayn-tizim (komponentlar kutubxonasi) va avtomatik testlar.
