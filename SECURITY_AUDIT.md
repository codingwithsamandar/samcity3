# 🔐 SamCity — Xavfsizlik auditi natijasi

Sana: 2026-06-26. Kod statik tahlil qilindi (settings, views, API, consumers,
to'lov shlyuzlari, SMS, fayl yuklash). Quyida tashqi auditdagi har bir band
bo'yicha javob + bu sessiyada kiritilgan tuzatishlar.

---

## A qism — Tashqi auditdagi 8 ta band

### 🔴 1, 3, 5. `.env` / `.env.production` ZIP ichida + SECRET_KEY oshkor
**Holat: tuzatildi (qisman) + harakat talab qilinadi.**
- Lokal `.env` dagi haqiqiy `SECRET_KEY` olib tashlandi — endi u yerda dev-only
  `django-insecure-...` qiymati turibdi (maxfiy emas).
- `.env` allaqachon `.gitignore` da — git'ga tushmaydi. Muammo: arxiv (ZIP)
  papkadan to'g'ridan yaratilganda `.env` ham kirib ketgan.
- **Siz qilishingiz kerak:**
  1. Agar loyiha GitHub'ga push qilingan bo'lsa va eski kalit u yerda bo'lsa —
     **kalitni darhol almashtiring** (yangi `SECRET_KEY` generatsiya qiling).
  2. Arxiv yuborishda `.env`, `.env.production`, `db.sqlite3`, `venv/` ni qo'shmang
     (pastdagi buyruq).
  3. Production kalitlar **faqat serverdagi `.env`** da bo'lsin.

### 🟠 2. `DJANGO_DEBUG=True`
**Holat: production'da hal qilingan.** Lokal `.env` da `True` (normal). Serverda
`.env.production` → `.env` ishlatiladi, u yerda `DJANGO_DEBUG=False`. `settings.py`
DEBUG=False bo'lганda HSTS, secure cookie, SSL redirect kabilarni avtomatik yoqadi.

### 🟡 4. SQLite ishlatilmoqda
**Holat: production'da PostgreSQL.** `db.sqlite3` faqat lokal dev uchun, `.gitignore`
va `.dockerignore` da. docker-compose'da PostgreSQL tayyor — `.env.production` da
`POSTGRES_*` to'ldirilganda avtomatik o'tadi. Serverga `db.sqlite3` ni ko'chirmang.

### 🟡 6. Repository juda katta (venv/ ~16k fayl)
**Holat: hal qilingan (packaging).** `venv/` `.gitignore` va `.dockerignore` da —
git va Docker image'ga kirmaydi. ZIP papkadan yaratilgani uchun kirib ketgan.
To'g'ri arxivlash: `venv/`, `.env*`, `db.sqlite3`, `media/`, `__pycache__` siz.

### 🟡 7, 8. ALLOWED_HOSTS / CSRF faqat localhost
**Holat: production shablonda hal qilingan.** `.env.production` da domen joyi bor:
`DJANGO_ALLOWED_HOSTS` va `CSRF_TRUSTED_ORIGINS` ga o'z domeningizni yozasiz.

**To'g'ri arxiv yaratish (Windows PowerShell misol):**
```powershell
# venv, .env, db.sqlite3, media, cache fayllarsiz arxiv
Compress-Archive -Path * -DestinationPath samcity.zip -Force
# (avval keraksizlarni o'chiring — pastdagi "tozalash" bo'limiga qarang)
```

---

## B qism — "Tekshirilmagan" xavfsizlik jihatlari (chuqur audit)

| # | Jihat | Verdikt | Izoh |
|---|-------|---------|------|
| 1 | **SQL Injection** | ✅ Xavfsiz | `.raw()`, `.extra()`, `cursor.execute`, RawSQL — **umuman yo'q**. Hammasi Django ORM (parametrlangan). |
| 2 | **XSS** | ✅ Xavfsiz | `mark_safe` / `|safe` — **hech qayerda ishlatilmagan**. Django auto-escape yoqilgan. JS'da `escapejs`. |
| 3 | **CSRF** | ✅ To'g'ri | `CsrfViewMiddleware` faol; formalarда token; webhook'lar (`csrf_exempt`) imzo/Basic-auth bilan himoyalangan. |
| 4 | **JWT** | ✅ Yaxshi | `ROTATE_REFRESH_TOKENS=True`, access 60min, refresh 30kun, `UPDATE_LAST_LOGIN`. Maxfiy kalitga bog'liq — kalit serverda. |
| 5 | **Password hashing** | ✅ To'g'ri | Django default PBKDF2; `AUTH_PASSWORD_VALIDATORS` (uzunlik, umumiy parol, raqamli) yoqilgan. |
| 6 | **Rate limiting** | ✅ Kuchli | DRF throttling (anon 60/min, user 300/min, OTP 5/min, login 10/min, checkout 20/min) + cache-asosli `ratelimit` dekorator. |
| 7 | **Permission tekshiruvi** | ✅ Asosan to'g'ri | Egalik tekshiruvlari view'larda bor (do'kon/joy/venue/order); analitika `@staff_member_required`; DRF `IsAuthenticatedOrReadOnly` + custom permissions. |
| 8 | **IDOR** | 🟠 1 ta topildi → **tuzatildi** | Chat `forward_message` istalgan xonadan xabar uzata olardi → endi faqat a'zo bo'lgan xonadan. Boshqa joylarda `get_object_or_404(..., user=request.user)` ishlatilgan. |
| 9 | **File upload** | 🟢 Yaxshi (kichik tavsiya) | Kengaytma + hajm (5MB) tekshiriladi; `ImageField`+Pillow haqiqiy rasmni validatsiya qiladi; media nginx'dan statik beriladi (kod bajarilmaydi). Tavsiya: Pillow `verify()` qo'shsa yanada mustahkam. |
| 10 | **API autentifikatsiya** | ✅ To'g'ri | JWT + Session; default permission `IsAuthenticatedOrReadOnly`; throttling yoqilgan. |
| 11 | **CORS** | ✅ To'g'ri | `CORS_ALLOW_ALL_ORIGINS` faqat DEBUG'da; production'da `CORS_ALLOWED_ORIGINS` aniq domenlar bilan. |
| 12 | **SSRF** | ✅ Xavfsiz | Tashqi so'rovlar (Nominatim/OSRM geocoding, SMS) — **host qat'iy belgilangan** (env'dan), foydalanuvchi faqat `lat/lon` (float) beradi. URL inyeksiya yo'q. |
| 13 | **Command Injection** | ✅ Xavfsiz | `os.system`, `subprocess`, `eval`, `exec`, `pickle`, `yaml.load` — **umuman yo'q**. |
| 14 | **Path Traversal** | ✅ Xavfsiz | Fayl nomlari `uuid` bilan generatsiya qilinadi; foydalanuvchi yo'l (path) bermaydi; media `MEDIA_ROOT` ichida. |
| 15 | **WebSocket auth** | ✅ To'g'ri | Barcha consumer'lar (chat/taxi/delivery/notifications) `is_authenticated` tekshiradi; JWT middleware (token query/header); chatda member/ban/admin tekshiruvi. |
| 16 | **Redis xavfsizligi** | 🟡 Sozlash | docker-compose'da Redis ichki tarmoqда (tashqariga port ochilmagan) — yaxshi. Tavsiya: `requirepass` qo'shing, tashqi serverда bo'lsa firewall bilan yoping. |
| 17 | **Docker konteyner** | ✅ Yaxshi | Multi-stage build, **non-root `appuser`**, minimal slim image, healthcheck. |
| 18 | **Nginx** | 🟢 Yaxshi (HTTPS yoqilsin) | `client_max_body_size`, gzip, WS upgrade, statik/media to'g'ridan. HTTPS bloki tayyor — sertifikat olib yoqing (DEPLOY.md 5-bo'lim). |
| 19 | **GitHub Actions secrets** | ⚪ Mavjud emas | CI/CD sozlanmagan. Agar qo'shsangiz: sirlarni faqat **GitHub Secrets** da saqlang, hech qachon kodga yozmang. |

---

## C qism — Bu sessiyada kiritilgan tuzatishlar

1. ✅ Lokal `.env` dagi haqiqiy `SECRET_KEY` neytrallandi (dev-only qiymat).
2. ✅ Chat `forward_message` IDOR yopildi (`main/consumers.py`).
3. ✅ Payme webhook (`payme.py`) — `atomic + select_for_update` (ikki marta to'lov oldi olindi).
4. ✅ Click webhook (`click.py`) — xuddi shunday qator qulfi.
5. ✅ `nginx.conf` — gzip; HTTPS redirect-loop oldini olish (`SECURE_SSL_REDIRECT` env orqali).
6. ✅ `.env.production` + `DEPLOY.md` — to'liq production shablon va qo'llanma.

---

## D qism — Sizdan talab qilinadigan harakatlar (eng muhim)

1. 🔴 **Agar eski `SECRET_KEY` GitHub'ga chiqqan bo'lsa — darhol almashtiring.**
2. 🔴 Server `.env` da haqiqiy yangi kalit + `DEBUG=False` + domen + SMS kalitlari.
3. 🟡 Arxiv/repo'dan keraksizlarni tozalang:
   ```bash
   rm -f errors.txt check.txt urls.txt find_urls.py replace_urls.py test_templates.py
   # ZIP yaratishda qo'shmang: venv/  .env*  db.sqlite3  media/  __pycache__/
   ```
4. 🟡 Redis'ga parol (`requirepass`) qo'ying (tashqi serverда bo'lsa).
5. 🟢 HTTPS'ni yoqing (DEPLOY.md 5-bo'lim) va `SECURE_SSL_REDIRECT=True` qiling.
6. 🟢 Deploy'dan keyin: `python manage.py check --deploy` va `python manage.py test`.

> **Umumiy xulosa:** kod xavfsizligi darajasi yuqori — injection/XSS/SSRF/command-injection
> sinflari toza, auth va rate-limiting kuchli. Asosiy xavf — **kod emas, sozlama/sir
> boshqaruvi** (oshkor bo'lgan `.env`/SECRET_KEY). Yuqoridagi D-qismni bajarsangiz,
> 1000 foydalanuvchi uchun xavfsiz holatda bo'lasiz.
