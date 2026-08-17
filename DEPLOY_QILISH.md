# SamCity — Render.com'ga deploy qilish (amaliy yo'riqnoma)

**Holat (2026-08-17):**
- ✅ Bepul tarif (web + PostgreSQL, worker va Redis o'chiq)
- ✅ Telegram token keyinroq kiritiladi
- ✅ Media (Supabase S3) hozircha o'chiq — rasm efemer diskda (test uchun)
- ✅ Superuser `DJANGO_SUPERUSER_PHONE` + `DJANGO_SUPERUSER_PASSWORD` orqali avtomatik

---

## 1-qadam: render.com'da Blueprint ochish (5 daqiqa)

1. Brauzerda [https://dashboard.render.com](https://dashboard.render.com) ga kiring.
2. **GitHub** orqali login qiling (birinchi marta bo'lsa Render'ga ruxsat bering).
3. Yuqori o'ng burchakdagi **New +** → **Blueprint** ni bosing.
4. **Repository** qismida `codingwithsamandar/samcity3` ni tanlang.
   > Agar chiqmasa: "Configure account" → GitHub'da `codingwithsamandar/samcity3` reposiga Render access bering.
5. Render `render.yaml` ni o'qiydi va shuni ko'rsatadi:
   - `samcity` — Web Service (Docker, frankfurt, free)
   - `samcity-db` — PostgreSQL (free)
6. **Apply** ni bosing. Render 5-7 daqiqada ikkalasini yaratadi va birinchi build boshlanadi.

> ⏳ Build tugagach `https://samcity.onrender.com` (yoki Render bergan nom) ochiladi.

---

## 2-qadam: Maxfiy env o'zgaruvchilarni qo'lda kiritish

`render.yaml`'da `sync: false` bilan belgilanganlar **avtomatik kiritilmaydi** — Render panelida qo'lda qo'shasiz.

### A) Admin (superuser) — MAJBURIY

1. Render Dashboard → `samcity` → **Environment** → **Add Environment Variable**
2. Quyidagilarni qo'shing (o'zingizning telefon va parol bilan):

| Key | Qiymat | Izoh |
|---|---|---|
| `DJANGO_SUPERUSER_PHONE` | `+998901234567` | O'zingizning telefon raqamingiz |
| `DJANGO_SUPERUSER_PASSWORD` | `<kuchli parol>` | Kamida 8 belgi |

3. **Save** → xizmat avtomatik qayta deploy bo'ladi (1-2 daqiqa).
4. Deploy loglarida shu qator ko'rinishi kerak:
   ```
   ▶ Superuser tekshirilmoqda/yaratilmoqda (+998901234567)...
   ```
5. Tekshirish: `https://samcity.onrender.com/admin/` → telefon + parol bilan kiring.

### B) Telegram bot — KEYINROQ (ixtiyoriy)

Hali kiritmasangiz — OTP kodlari `SMS_BACKEND=console` orqali Render loglarida ko'rinadi (test uchun yaxshi).

Keyinroq qo'shmoqchi bo'lsangiz:
1. Telegram'da [@BotFather](https://t.me/BotFather) → `/newbot` → nom + username → token oling.
2. Render → `samcity` → Environment → qo'shing:

| Key | Qiymat |
|---|---|
| `TELEGRAM_BOT_TOKEN` | `<botfather bergan token>` |
| `TELEGRAM_BOT_USERNAME` | `<bot username, masalan samcity_bot>` |

3. Save → qayta deploy.
4. Tekshirish: `https://t.me/<username>` → `/start`.

### C) SMS (Eskiz) — KEYINROQ (ixtiyoriy)

Hali kiritilmaydi — `SMS_BACKEND=console` (kodlar logda).

---

## 3-qadam: Birinchi marta tekshirish

Build tugagach:

| Tekshirish | URL | Kutgan natija |
|---|---|---|
| Healthcheck | `https://samcity.onrender.com/api/health/` | `{"ok": true, ...}` yoki shunga o'xshash JSON |
| Admin panel | `https://samcity.onrender.com/admin/` | Login formasi (Django admin) |
| Asosiy sahifa | `https://samcity.onrender.com/` | SamCity bosh sahifa |

### Muammolar:

- **Build xato** → Render → Logs → `entrypoint.sh` oxiridagi xabarni toping. Ko'pincha `migrate` yoki `collectstatic` xatosi.
- **502 Bad Gateway** → Daphne hali ishga tushmagan — 30 soniya kuting va qayta urinib ko'ring.
- **DisallowedHost** → Render avtomatik `.onrender.com` ni qo'shadi, qo'lda o'zgartirish shart emas.
- **Login ishlamayapti** → OTP backend sozlanmagan. Yuqoridagi **B** yoki **C** qadamga qarang. Hozircha `SMS_BACKEND=console` — kodlar logda.

---

## 4-qadam: Demo ma'lumot (ixtiyoriy)

Agar bo'sh saytdan demo ma'lumot kerak bo'lsa:

1. Render → `samcity` → Environment → `SEED_DEMO=false` ni **Add Environment Variable** bilan `true` ga o'zgartiring.
2. Save → qayta deploy (~2-3 daqiqa).
3. Deploy loglarida `seed_all` qatorlari ko'rinadi.
4. **Muhim:** ishlatgach yana `false` qilib qo'ying (aks holda har deploy'da qayta ishlaydi — idempotent, lekin vaqt oladi).

---

## Media (rasm) — keyinroq qo'shish

Hozircha rasm **efemer diskda** — har deploy'da yo'qoladi. Production'ga o'tishdan oldin qo'shish kerak:

### A) Cloudinary (eng oson, bepul 25GB)

1. [https://cloudinary.com](https://cloudinary.com) → ro'yxatdan o'ting → Dashboard'dan `Cloud Name`, `API Key`, `API Secret` oling.
2. Render → `samcity` → Environment:
   - `CLOUDINARY_CLOUD_NAME=<cloud_name>`
   - `CLOUDINARY_API_KEY=<api_key>`
   - `CLOUDINARY_API_SECRET=<api_secret>`
3. Save → deploy. `render.yaml`'da CLOUDINARY_* env'larni yoqish kerak (hozircha yo'q — alohida ko'rsataman).

### B) Supabase S3 (hozir render.yaml'da izohga olingan)

`render.yaml`'dagi AWS_* 6 qatorning `#` larini olib tashlang va Render → Environment'ga AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY qo'shing. Bucket nomi: `media` (Public qiling).

---

## Tez-tez uchraydigan savollar

**S: Bepul tarifda sayt uxlab qoladimi?**
Ha — 15 daqiqa harakatsizlikdan keyin uxlaydi, keyingi tashrif ~1 daqiqada uyg'onadi. Demo uchun normal. Pulli `$7/oy` Starter doimiy.

**S: PostgreSQL bazasi qancha vaqt saqlanadi?**
Free tarif 1GB va 90 kunlik muddat bilan. Vaqti-vaqti bilan yangilab turish kerak.

**S: Admin panelga kimdir kirsa nima qilamiz?**
Superuser login/parolni Render Environment'dan o'zgartiring → save → qayta deploy. `createsuperuser` qayta ishlamaydi, shuning uchun eski user'ni o'chirish uchun lokal'da management command ishlatish kerak.

**S: Telegram bot 409 Conflict xato beradi?**
Bu bir token bilan ikki joyda polling ishlayotganini anglatadi. Bitta joyda qoldiring.

**S: Domena ulash (samcity.uz) mumkinmi?**
Ha — Render → Settings → Custom Domains → DNS CNAME qo'ying (masalan `samcity.uz` → `samcity.onrender.com`). SSL avtomatik.

---

## Xulosa

| Qadam | Kim | Vaqt |
|---|---|---|
| 1. Blueprint ochish | **Siz** | 5 daq |
| 2A. Admin env | **Siz** | 2 daq |
| 3. Tekshirish | **Siz** | 5 daq |
| 2B. Telegram token | Keyinroq | 5 daq |
| 4. Demo seed | Ixtiyoriy | 3 daq |
| Media (Cloudinary) | Production oldidan | 10 daq |

**Birinchi muvaffaqiyat belgisi:** `https://samcity.onrender.com/api/health/` JSON qaytarsa va admin panelga kirsa bo'ldi. ✅
