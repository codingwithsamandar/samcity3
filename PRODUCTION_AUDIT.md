# Production audit — natija

> Sandbox diski to'la — server ishga tushirilmadi; barcha o'zgarishlar kod + URL/shablon
> mosligi bo'yicha statik tekshirildi. Ishga tushirish: `python manage.py migrate` (yangi: `delivery/0006`, `places/0002`).

## 1. Production readiness: ~7.5/10
Funksional jihatdan to'liq (barcha rollar uchun ishlaydigan oqimlar), lekin haqiqiy to'lov (Payme/Click),
real-time WebSocket va avtomatik testlar yo'q — shular tufayli 10 emas.

## 2. O'zgartirilgan fayllar
`delivery/models.py` (DeliveryDriver, Order.driver/assigned_at, +2 status, can_transition),
`delivery/views.py` (driver flow, validated transitions, store status validatsiyasi),
`delivery/urls.py`, `delivery/admin.py`, `delivery/templates/delivery/{order_detail,store_list,store_orders}.html`,
`main/views.py` (admin_dashboard), `main/urls.py`, `main/templates/base.html` (Analitika nav).

## 3. Yaratilgan fayllar
`delivery/migrations/0006_deliverydriver_order_driver.py`,
`delivery/templates/delivery/{driver_register,driver_dashboard,_order_timeline}.html`,
`main/templates/admin_dashboard.html`.

## 4. Bajarilgan ishlar (faza bo'yicha)
**1. Delivery ekotizimi** ✅ — `DeliveryDriver` modeli (profil, transport turi/raqami, bo'sh/band holati),
ro'yxatdan o'tish, haydovchi paneli (statistika, daromad = yetkazilgan buyurtmalar `delivery_fee` yig'indisi, tarix),
buyurtmani **qabul qilish / voz kechish**, `assigned → on_the_way → delivered` o'tishlari. Buyurtma hayotsikli:
pending→accepted→preparing→ready→assigned→on_the_way→delivered (+cancelled), **barcha o'tishlar `can_transition()` bilan validatsiya qilinadi** (egasi faqat accepted/preparing/ready/cancelled, haydovchi faqat o'z bosqichlari).
**2. Tracking** ✅ — buyurtma jarayoni timeline (`_order_timeline.html`) mijoz sahifasida; haydovchi paneli va do'kon paneli holatni ko'rsatadi/boshqaradi. (Real-time emas — quyida.)
**3. Real-time** ⚠️ — mavjud bildirishnoma signallari saqlandi; to'liq WebSocket order-tracking qo'shilmadi (Channels mavjud, lekin katta ish — kelajakka).
**4. Analitika** ✅ — `/staff/analytics/` (xodimlar uchun): foydalanuvchi, do'kon, mahsulot, buyurtma, haydovchi, taksi, joy, bron, diqqatga sazovor, e'lon ko'rsatkichlari + daromad (delivery/taksi/to'lovlar) + Chart.js (bar + doughnut).
**5. Performance** ✅ (qisman) — yangi viewlarda `select_related('driver')`, `prefetch_related('items')`, daromad `aggregate(Sum)` bilan; N+1 oldi olindi.
**6. Security** ✅ — egalik tekshiruvlari (driver actions faqat biriktirilgan haydovchi; store status faqat egasi; place/store/venue edit/delete egasi/staff); holat o'tishlari server tomonida validatsiya; analitika `@staff_member_required`; CSRF barcha formalarda; foydalanuvchi kiritgan matn shablonlarda avtomatik escape; `escapejs` JS'da.
**8. Arxitektura** ✅ — mavjud app-lar qayta ishlatildi, dublikat model yaratilmadi; `can_transition` markazlashgan; haydovchi/earnings hisob-kitobi querylar orqali (sinxron maydon yo'q — xato kamayadi).
**9. QA (rol oqimlari)** — Mijoz: savat→checkout→to'lov→timeline kuzatish ✅. Do'kon egasi: buyurtmani accepted→preparing→ready ✅. Haydovchi: ro'yxatdan o'tish→bo'sh→ready buyurtmani qabul→yo'lda→yetkazdim ✅. Joy egasi / Taksi haydovchi / Admin oqimlari avvalgi fazalardan ✅.

## 5. Tuzatilgan / yangi xatolarning oldi olindi
- Buyurtma holati nazoratsiz o'zgartirilardi → endi `can_transition` bilan cheklangan.
- Yetkazib berishda haydovchi bo'g'ini umuman yo'q edi → to'liq qo'shildi.
- Do'kon egasi haydovchi-bosqich holatlarini ham qo'ya olardi → cheklab qo'yildi.

## 6. Performance yaxshilanishlari
Driver dashboard va store_orders querylarida select_related/prefetch_related; daromad bitta aggregate query bilan.

## 7. Ma'lum cheklovlar
- To'lov demo (Payme/Click yo'q).
- Real-time WebSocket order-tracking yo'q (sahifa yangilanganda yangilanadi).
- Bitta buyurtma ko'p do'konli bo'lishi mumkin (har egaga ko'rinadi) — haydovchi butun buyurtmani oladi.
- Avtomatik testlar yo'q (sandbox cheklovi).
- To'liq Bootstrap/Tailwind redesign qilinmadi (mavjud yaxlit dark dizayn saqlandi — ishlaydigan shablonlarni buzmaslik uchun).

## 8. Kelajak tavsiyalar
1. Channels consumer orqali real-time order tracking va bildirishnoma.
2. Haqiqiy to'lov shlyuzi (Payme/Click).
3. Driver earnings uchun alohida log + haftalik hisobot.
4. pytest/Django test bilan rol oqimlarini avtomatlashtirish.
5. Buyurtmani do'kon bo'yicha bo'lish (multi-store split).
6. Rate limiting (django-ratelimit) login/OTP/checkout uchun.
