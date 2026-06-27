# SamCity — Demo qo'llanma

Bu hujjat loyihani demo ma'lumotlar bilan ishga tushirish va ko'rsatish uchun.

---

## 1. Ishga tushirish (eng oson yo'l)

**Windows:** `run_demo.bat` faylini ikki marta bosing.

**macOS / Linux:** terminalda `bash run_demo.sh`.

Skript o'zi virtual muhit yaratadi, kutubxonalarni o'rnatadi, bazani tayyorlaydi,
demo ma'lumotlarni yuklaydi va serverni ishga tushiradi.

Brauzerda oching: **http://127.0.0.1:8000/**

### Qo'lda ishga tushirish (agar skript ishlamasa)

```
python -m venv .venv
.venv\Scripts\activate        REM  (Windows)
source .venv/bin/activate       #   (macOS/Linux)
pip install -r requirements.txt
python manage.py seed_all
python manage.py runserver
```

Ma'lumotlarni tozalab qaytadan yuklash: `python manage.py demo_data --clear`

---

## 2. Demo hisoblar

Foydalanuvchi paroli: **demo1234**

| Telefon | Ism | Rol |
|---|---|---|
| +998901234567 | Sardor Aliyev | foydalanuvchi (e'lon, rezyume) |
| +998902345678 | Malika Yusupova | foydalanuvchi (o'qituvchi) |
| +998903456789 | Bobur Karimov | biznes (e'lon/joy egasi) |
| +998904567890 | Nilufar Rashidova | foydalanuvchi (HR) |
| +998905678901 | Jasur Toshmatov | haydovchi |

**Admin:** +998900000000 — parol **admin1234** → `/admin/` va boshqaruv paneli.

> Kirish: `/login/` sahifasida telefon raqami va parolni kiriting.

---

## 3. Asosiy sahifalar

| Bo'lim | Havola |
|---|---|
| Bosh sahifa (e'lonlar) | `/` |
| Barcha e'lonlar | `/all-ads/` |
| Ish e'lonlari | `/jobs/` |
| Rezyumelar | `/resumes/` |
| Taksi | `/taxi/` · xarita: `/taxi/map/` |
| Yetkazib berish (do'konlar) | `/delivery/` · savat: `/delivery/cart/` |
| To'lovlar | `/payments/` |
| Joy bron qilish | `/booking/` |
| Xarita / joylar | `/map/` · yaqin-atrof: `/map/nearby/` |
| Mahalla chati | `/neighborhood-chat/` |
| So'rovnomalar / yordam | `/community/polls/` · `/community/help/` |
| Kommunal to'lovlar | `/utilities/` |
| Yagona boshqaruv paneli | `/dashboard/` |
| Profil | `/profile/` |
| Statistika (admin) | `/staff/analytics/` |
| Django admin | `/admin/` |

---

## 4. Demo ko'rsatish ssenariysi (~5 daqiqa)

1. **Bosh sahifa** (`/`) — xizmatlar bloki va so'nggi e'lonlarni ko'rsating.
2. **Kirish** (`/login/`) — `+998903456789 / demo1234` (Bobur, biznes egasi).
3. **E'lon** — birorta e'lonni oching, "Bron qilish" yoqilgan ofis e'loniga o'ting (`/booking/`), sana tanlab bron qiling.
4. **Yetkazib berish** (`/delivery/`) — do'konga kiring, mahsulotni savatga qo'shing (`/delivery/cart/`), checkout qiling.
5. **Taksi** (`/taxi/`) — taksist profilini oching, marshrut bo'yicha buyurtma bering; xaritani (`/taxi/map/`) ko'rsating.
6. **Boshqaruv paneli** (`/dashboard/`) — bitta joyda buyurtmalar, bronlar, do'konlar, rezyumelarni ko'rsating.
7. **Mahalla chati** (`/neighborhood-chat/`) — real-time xabarlarni ko'rsating.
8. **Admin** — `/login/` orqali `+998900000000 / admin1234`, so'ng `/admin/` va `/staff/analytics/`.

---

## 5. Demoda nimalar bor (INVESTOR darajasi)

`seed_all` (yoki alohida `seed_demo_full`) quyidagilarni yuklaydi — Shofirkon brendi bilan:

- **~32 fuqaro + ~16 biznes egasi + 22 taksist** foydalanuvchi (parol: `demo1234`) + 1 admin
- **~56 xarita joyi**: restoranlar, dorixonalar, shifoxonalar/klinikalar, mehmonxonalar, to'yxonalar, banklar, davlat idoralari, ta'lim markazlari, pochta, elektronika, mebel, diqqatga sazovor joylar — har birida baho/sharhlar
- **~55 do'kon + 350+ mahsulot** (12 kategoriya: oziq-ovqat, restoran, dorixona, elektronika, go'zallik, sport, kiyim, bolalar, qurilish, ...)
- **22 taksist** — mashina, AB marshrutlar, 3 ta taksi xizmati (1265/1187/1133), online haydovchilar xaritada
- **16 venue** (to'yxona/restoran/kafe/salon/sport) + turli holatdagi bronlar
- **22 to'lov muassasasi** (kommunal, internet, kurs, bog'cha, maktab)
- **24+ marketplace e'loni** (uy-joy, avtomobil, xizmat, hayvonlar)
- mahalla chati, kommunal to'lovlar tarixi, rezyume/ish e'lonlari (demo_data dan)

### Faqat boy demo ma'lumotni qayta yuklash
```
python manage.py seed_demo_full            # qo'shadi (idempotent)
python manage.py seed_demo_full --clear    # faqat shu buyruq qo'shganini o'chiradi
```

**Eslatma:** to'lovlar demo rejimida (Payme/Click ulanmagan) — "to'lash" tugmasi holatni o'zgartiradi, haqiqiy pul o'tmaydi. Joylar/do'konlarda rasm yo'q (ImageField bo'sh) — UI ularni ikonka/placeholder bilan ko'rsatadi.
