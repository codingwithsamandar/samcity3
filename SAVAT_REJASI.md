# 🛒 Savat (Cart) bo'limi — rivojlantirish rejasi

## Hozirgi holat (mavjud)

`delivery` ilovasida savat backendi allaqachon ishlaydi:

- **Modellar:** `Cart` (foydalanuvchiga bog'langan) va `CartItem` (mahsulot + miqdor).
- **Amallar** (`cart_views.py`): savatga qo'shish, o'chirish, miqdorni oshirish/kamaytirish — AJAX va oddiy POST ikkalasini qo'llab-quvvatlaydi.
- **Sahifa:** `/delivery/cart/` (`cart_view`) — savat ko'rinadi.
- **Hisob-kitob:** `get_subtotal`, `get_total_quantity`, `get_total_items` metodlari bor.
- **Navbar:** savatdagi mahsulotlar soni "badge" sifatida ko'rsatiladi.

**Yetishmayotgan asosiy narsa:** savatdan keyingi bosqich yo'q — ya'ni **buyurtma berish (checkout), manzil, to'lov va buyurtma tarixi** yo'q.

---

## Bosqichma-bosqich reja

### 1-bosqich — Buyurtma (Order) modeli
Savatni haqiqiy buyurtmaga aylantirish uchun yangi modellar:

- **`Order`**: `user`, `status` (yangi / tasdiqlangan / yo'lda / yetkazildi / bekor), `delivery_address`, `phone`, `note`, `subtotal`, `delivery_fee`, `total`, `payment_status` (to'langan/naqd), `created_at`.
- **`OrderItem`**: `order`, `product` (yoki nomi/narxi snapshot), `quantity`, `price` — buyurtma paytidagi narxni saqlash uchun (mahsulot narxi keyin o'zgarsa ham chek o'zgarmaydi).

> Eslatma: bitta savatda turli do'konlardan mahsulot bo'lishi mumkin. Qaror kerak: **bitta buyurtma = bitta do'kon** (savatni do'kon bo'yicha ajratish) yoki aralash buyurtma. Tavsiya: do'kon bo'yicha ajratish (yetkazib berish mantig'i sodda bo'ladi).

### 2-bosqich — Checkout (rasmiylashtirish) sahifasi
- `/delivery/checkout/` sahifasi: savat xulosasi + **manzil**, **telefon**, **izoh** maydonlari.
- Yetkazib berish narxi (`delivery_fee`) — masofa yoki belgilangan tarif (demo uchun: belgilangan, masalan 10 000 so'm).
- "Buyurtmani tasdiqlash" tugmasi → `Order` yaratadi va to'lovga o'tadi.

### 3-bosqich — To'lov (demo, taksi/payments kabi)
- Allaqachon yozilgan **demo karta to'lovi** namunasidan foydalanamiz (Uzcard/Humo/Visa aniqlash, "To'lash" bosilsa → to'langan).
- To'lov usullari: **Karta (demo)** yoki **Yetkazib berishda naqd**.
- To'lov yakunlangach: `Order.status = 'confirmed'`, savat tozalanadi, mahsulot zaxirasi (`stock`) kamayadi.
- Payme/Click keyinroq shu joyga ulanadi.

### 4-bosqich — Buyurtma tasdig'i va tarix
- `/delivery/order/<id>/` — buyurtma cheki (mahsulotlar, summa, manzil, holat).
- `/delivery/orders/` — "Mening buyurtmalarim" ro'yxati.
- Do'kon egasi uchun: kelgan buyurtmalar ro'yxati + holatni o'zgartirish (tasdiqlash, yo'lda, yetkazildi).

### 5-bosqich — Mustahkamlash va qulayliklar
- **Zaxira tekshiruvi:** buyurtma paytida stock yetarliligini qayta tekshirish.
- **Bo'sh savat** holati va xatoliklarni chiroyli ko'rsatish.
- **Admin panel:** `Order`/`OrderItem` ni ro'yxatga olish, holat bo'yicha filtr.
- **Demo ma'lumot:** `seed_orders` (ixtiyoriy) — namuna buyurtmalar.
- **Bildirishnoma** (keyinroq): yangi buyurtma kelganda do'kon egasiga xabar.

---

## Taklif qilingan fayllar
```
delivery/models.py          → Order, OrderItem qo'shish
delivery/views.py           → checkout, order_payment, order_detail, my_orders, (egasi uchun) store_orders
delivery/urls.py            → yangi yo'llar
delivery/admin.py           → Order, OrderItem
delivery/templates/delivery/→ checkout.html, order_payment.html, order_detail.html, my_orders.html
delivery/migrations/        → 0004_order_orderitem
```

## Tavsiya etilgan tartib
1-bosqich (model) → 2 (checkout) → 3 (to'lov) → 4 (tarix) → 5 (mustahkamlash).

Eng katta qaror: **buyurtma do'kon bo'yicha ajratilsinmi yoki aralash bo'lsinmi.** Shuni tasdiqlasangiz, 1–4 bosqichlarni amalda yozib beraman.
