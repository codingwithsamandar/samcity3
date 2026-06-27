# 🔍 Sayt tekshiruvi — rollar bo'yicha kamchiliklar

> Eslatma: sandbox diski to'la bo'lgani uchun serverni ishga tushira olmadim.
> Bu hisobot — kodni rollar oqimi bo'yicha chuqur statik tahlil natijasi.
> Barcha `{% url %}` havolalari tekshirildi — **NoReverseMatch yo'q** (havolalar butun).

---

## ✅ Darhol tuzatildi
- **profile.html** — o'chirilgan `Business` modeliga havola (`user.businesses.count`) "Bizneslar" statistikasini buzar/bo'sh ko'rsatardi. `user.stores.count` ("Do'konlar") ga almashtirildi.

---

## 🔴 Muhim kamchiliklar (funksiya yetishmaydi)

### 1. Biznes egasi do'kon/mahsulot qo'sha olmaydi (sayt orqali)
`delivery` ilovasida `store_create` / `product_create` view va sahifa **yo'q**. Do'kon va mahsulotlar faqat **admin panel** orqali kiritiladi. Biznes roli foydalanuvchisi o'z do'konini sayt interfeysidan ocholmaydi.
→ Kerak: `store_create`, `store_edit`, `product_create`, `product_edit` (egasi uchun) + do'kon boshqaruv paneli.

### 2. Haydovchi (taksist) o'zini ro'yxatdan o'tkaza olmaydi
Taksistlar va ularning marshrutlari faqat admin/`seed_taxi` orqali yaratiladi. Haydovchi roli foydalanuvchisi sayt orqali taksist profili yoki AB marshrut qo'sholmaydi.
→ Kerak: taksist profil yaratish/tahrirlash sahifasi.

### 3. Delivery buyurtmalarini do'kon egasi boshqara olmaydi
Buyurtma (Order) holatini (yangi → yo'lda → yetkazildi) faqat admin o'zgartiradi. Do'kon egasi uchun "kelgan buyurtmalar" paneli yo'q (booking/manage_bookings ga o'xshash).

---

## 🟡 O'rta darajadagi kamchiliklar

### 4. Joy (venue) bron — sana to'qnashuvi tekshirilmaydi
`venue_book` bir kun allaqachon band bo'lsa ham yangi bron yarataveradi (detail sahifada band sanalar ko'rsatiladi, lekin formada bloklanmaydi). Bir kunga ikki to'y broni mumkin bo'lib qoladi.
→ Kerak: bron paytida sana bandligini tekshirish.

### 5. Joy egasi venue'ni tahrirlay/o'chira olmaydi
`venue_create` bor, lekin `venue_edit` / `venue_delete` yo'q. Xato kiritilgan joyni egasi tuzata olmaydi (faqat admin).

### 6. Rezyumelar mehmonlarga ko'rinmaydi
`resume_list` `@login_required`. Mehmon ish e'lonlarini (jobs) ko'ra oladi, lekin rezyumelarni ko'rish uchun login talab qilinadi — nomutanosib.

### 7. Foydalanuvchi faoliyati tarqoq
Bronlar/buyurtmalar har xil joyda: `/bookings/` (e'lon bronlari), `/booking/my/` (joylar), `/taxi/trips/`, `/delivery/orders/`, `/payments/my/`. Profil yon menyusida hammasi yo'q. Yagona "Mening faoliyatim" paneli foydali bo'lardi.

---

## 🟢 Kichik / UX

8. **Delivery checkout** — agar foydalanuvchining savati umuman yaratilmagan bo'lsa, `/delivery/checkout/` to'g'ridan-to'g'ri ochilsa 404 beradi (odatda savat orqali kelinadi, shuning uchun kam uchraydi). `get_or_create` bilan yumshatish mumkin.
9. **Taksi sharhlari nomutanosib** — taksistga baho faqat sayohatdan keyin, lekin taksi *xizmatiga* (1265) istalgan login qilgan foydalanuvchi baho bera oladi. Atayin bo'lishi mumkin.
10. **home.html mock tugmalar** — bosh sahifadagi ayrim `onclick="openModal(...)"` tugmalar (komunal, kitob va h.k.) haqiqiy sahifaga ulanmagan, namuna sifatida turibdi.
11. **Production sozlamalari** — `DEBUG=True`, `ALLOWED_HOSTS='*'`, kodga yozilgan `SECRET_KEY`. Productionga chiqishdan oldin `.env` orqali o'rnatilishi shart.

---

## Rollar bo'yicha qisqacha xulosa

| Rol | Ishlaydi | Yetishmaydi |
|-----|----------|-------------|
| **Mehmon** | Bosh sahifa, e'lonlar, taksi, joylar, do'konlar, to'lovlar ro'yxati | Rezyumelar (login talab), savat/bron (login talab — normal) |
| **Foydalanuvchi** | E'lon berish, bron, taksi, delivery+checkout, to'lov, chat, ish/rezyume | Yagona faoliyat paneli yo'q |
| **Biznes** | Joy qo'shish/bron boshqarish | ❗ Do'kon/mahsulot qo'shish (faqat admin), buyurtma boshqaruvi |
| **Haydovchi** | — | ❗ Taksist profil/marshrut qo'shish (faqat admin) |
| **Admin** | To'liq admin panel | — |

---

## Tavsiya etilgan ustuvorlik
1. Biznes egasi uchun do'kon/mahsulot qo'shish (eng katta bo'shliq).
2. Venue sana to'qnashuvini tekshirish (mantiqiy xato).
3. Delivery buyurtma boshqaruvi (do'kon egasi).
4. Taksist self-registration.
5. Qolgan UX yaxshilashlar.
