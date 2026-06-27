# SamCity — Render.com'ga bepul deploy qilish

Loyiha Render uchun tayyorlandi. Kerakli o'zgarishlar kiritildi:

- `whitenoise` qo'shildi — statik fayllar (admin, CSS) nginx'siz ishlaydi.
- `render.yaml` yaratildi — web service + bepul PostgreSQL avtomatik sozlanadi.
- `.gitattributes` qo'shildi — `entrypoint.sh` Linux'da to'g'ri ishlashi uchun.

---

## 1-qadam: Kodni GitHub'ga yuklash

Loyiha papkasida terminal oching va:

```bash
git init
git add .
git commit -m "Render deploy tayyorligi"
```

GitHub'da yangi **bo'sh** repo yarating (masalan `samcity`), so'ng:

```bash
git remote add origin https://github.com/FOYDALANUVCHI/samcity.git
git branch -M main
git push -u origin main
```

> `.gitignore` allaqachon `venv/`, `db.sqlite3`, `media/`, `.env` ni chiqarib tashlaydi — maxfiy narsalar yuklanmaydi.

---

## 2-qadam: Render'da Blueprint orqali deploy

1. [render.com](https://render.com) — bepul ro'yxatdan o'ting (karta kerak emas). GitHub bilan kiring.
2. **New → Blueprint** ni bosing.
3. `samcity` repo'ngizni tanlang. Render `render.yaml` ni avtomatik o'qiydi.
4. **Apply** bosing. Render quyidagilarni o'zi yaratadi:
   - `samcity` — web service (Docker, daphne ASGI)
   - `samcity-db` — bepul PostgreSQL (avtomatik ulanadi)
   - `DJANGO_SECRET_KEY` — avtomatik generatsiya qilinadi
5. Birinchi build ~3-5 daqiqa. Entrypoint o'zi `migrate` + `collectstatic` + `daphne` ni bajaradi.

Tugagach manzil: `https://samcity.onrender.com` (yoki Render bergan nom).

---

## 3-qadam: SMS sozlash (login ishlashi uchun MUHIM)

SMS bo'lmasa OTP/login ishlamaydi. Render panelida:
**samcity → Environment** bo'limiga kiring va to'ldiring:

- `SMS_ESKIZ_EMAIL` — eskiz.uz kabinetidagi email
- `SMS_ESKIZ_PASSWORD` — eskiz.uz paroli

Saqlagach service avtomatik qayta deploy bo'ladi.

> Tezda sinab ko'rish uchun SMS'siz: `SMS_BACKEND` ni `console` qiling — OTP kod Render loglarida ko'rinadi (faqat test uchun).

---

## 4-qadam: Admin yaratish

Render → samcity → **Shell** tabini oching va:

```bash
python manage.py createsuperuser
```

So'ng `https://samcity.onrender.com/admin/` orqali kiring.

---

## Bepul tarif cheklovlari (bilib qo'ying)

| Narsa | Cheklov | Yechim |
|---|---|---|
| Web service uxlashi | 15 daqiqa harakatsizlikdan keyin uxlaydi, ~1 daqiqa uyg'onish | Demo uchun normal. Doimiy ishlashi kerak bo'lsa Starter plan ($7/oy) |
| PostgreSQL | 1GB, 30 kundan keyin muddati tugaydi | 30 kunda yangilang yoki pulli bazaga o'ting |
| Media fayllar (rasmlar) | Disk vaqtinchalik — har deploy'da yuklangan rasmlar o'chadi | Doimiy kerak bo'lsa **Cloudinary** (bepul tarif) ulang |
| Redis | render.yaml'da yo'q | Bitta protsess uchun shart emas (in-memory ishlaydi). Miqyoslashda qo'shasiz |

---

## Tez-tez uchraydigan xatolar

- **502 / build muvaffaqiyatsiz** → Render → Logs ni tekshiring. Ko'pincha `entrypoint.sh` qator oxiri (CRLF) sababli — `.gitattributes` buni hal qiladi.
- **CSS yo'q / admin ko'rinishi buzilgan** → whitenoise qo'shilgan, lekin `collectstatic` ishlamagan bo'lishi mumkin. Logda `collectstatic` qatorini tekshiring.
- **DisallowedHost xatosi** → `DJANGO_ALLOWED_HOSTS` ichida `.onrender.com` borligini tekshiring (render.yaml'da bor).
- **Login ishlamayapti** → SMS sozlanmagan (3-qadam).
