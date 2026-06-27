# 🚀 SamCity — Serverga joylash qo'llanmasi (Production)

Bu loyiha Docker bilan to'liq tayyor: **web (daphne ASGI) + PostgreSQL + Redis + nginx**.
1000+ foydalanuvchi uchun pastdagi qadamlarni tartib bilan bajaring.

---

## 0. Kerakli narsalar

- Linux server (Ubuntu 22.04+ tavsiya), 2 vCPU / 4GB RAM (minimal), domen.
- Docker va Docker Compose o'rnatilgan:
  ```bash
  curl -fsSL https://get.docker.com | sh
  ```
- Domeningiz A-record'i shu server IP'siga yo'naltirilgan bo'lsin.

---

## 1. Kodni serverga olib chiqish

```bash
git clone <repo-url> samcity   # yoki rsync orqali yuklang
cd samcity
```

> ⚠️ `venv/`, `db.sqlite3`, `.env`, `media/` ni serverga **nusxalamang** —
> ular `.dockerignore` da, image ichiga kirmaydi va kerak emas.

---

## 2. Eski/keraksiz fayllarni tozalash (ixtiyoriy, lekin tavsiya etiladi)

Bular eski log/yordamchi fayllar, ishlashga ta'sir qilmaydi, ammo chalg'itadi:

```bash
rm -f errors.txt check.txt urls.txt find_urls.py replace_urls.py test_templates.py
```

*(Sandbox disk to'la bo'lgani uchun men bularni avtomatik o'chira olmadim — shu buyruqni o'zingiz ishlatib qo'ying.)*

---

## 3. Production `.env` faylini tayyorlash

Namuna shablon: **`.env.example`** (production qiymatlari bilan). Uni `.env` qilib nusxalang va to'ldiring:

```bash
cp .env.example .env
nano .env
```

> ⚠️ HTTPS (sertifikat) hali yo'q bo'lsa, `.env` da vaqtincha `SECURE_SSL_REDIRECT=False`
> qiling — aks holda HTTP'da cheksiz redirect bo'ladi. Sertifikat o'rnatgach True qiling.

**Majburiy o'zgartiriladigan qiymatlar:**

| Qiymat | Nima qilish kerak |
|--------|-------------------|
| `DJANGO_SECRET_KEY` | Yangi kalit generatsiya qiling (pastda) — dev kalitni ishlatmang! |
| `DJANGO_ALLOWED_HOSTS` | `samcity.uz,www.samcity.uz` (o'z domeningiz) |
| `CSRF_TRUSTED_ORIGINS` | `https://samcity.uz,https://www.samcity.uz` |
| `POSTGRES_PASSWORD` | Kuchli parol |
| `SMS_ESKIZ_EMAIL` / `SMS_ESKIZ_PASSWORD` | Eskiz.uz kabinetidan (bo'lmasa login ishlamaydi!) |

**SECRET_KEY generatsiya:**
```bash
docker run --rm python:3.12-slim python -c \
  "import secrets; print(''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#%^&*(-_=+)') for _ in range(64)))"
```
Chiqqan satrni `.env` dagi `DJANGO_SECRET_KEY=` ga qo'ying.

> 🔴 **Eng muhim 5 ta:** `DEBUG=False`, Postgres, Redis, ALLOWED_HOSTS, SMS kalitlari.
> Shularsiz sayt ochilmaydi yoki hech kim login qila olmaydi.

---

## 4. Birinchi ishga tushirish (HTTP — sertifikatdan oldin)

`.env` da hozircha `SECURE_SSL_REDIRECT=False` turganiga ishonch hosil qiling
(sertifikat hali yo'q — aks holda cheksiz redirect bo'ladi).

```bash
docker compose up -d --build
```

Bu avtomatik: bazani migrate qiladi → statik fayllarni yig'adi → daphne'ni ishga tushiradi.

Tekshirish:
```bash
curl http://SERVER_IP/api/health/      # {"status":"ok"} qaytishi kerak
docker compose logs -f web             # loglar
```

Superuser yarating (admin panel uchun):
```bash
docker compose exec web python manage.py createsuperuser
```

---

## 5. HTTPS o'rnatish (Let's Encrypt — bepul)

```bash
# 1) Certbot bilan sertifikat oling (server'da, 80-port bo'sh bo'lsin yoki webroot orqali)
sudo apt install certbot -y
sudo certbot certonly --webroot -w /var/www/certbot -d samcity.uz -d www.samcity.uz

# 2) Sertifikatlarni loyiha certs/ papkasiga ko'chiring
mkdir -p certs
sudo cp /etc/letsencrypt/live/samcity.uz/fullchain.pem certs/
sudo cp /etc/letsencrypt/live/samcity.uz/privkey.pem  certs/
```

Keyin:
1. **`nginx.conf`** da pastdagi `PRODUCTION HTTPS` blokidagi `#` larni oching,
   `server_name` ga domeningizni yozing. HTTP `location /` ni `return 301 https://$host$request_uri;` ga almashtiring.
2. **`.env`** da `SECURE_SSL_REDIRECT=True` qiling.
3. Qayta ishga tushiring:
   ```bash
   docker compose up -d
   ```

Sertifikatni avtomatik yangilash (cron):
```bash
0 3 * * * certbot renew --quiet && docker compose restart nginx
```

---

## 6. Tekshiruv ro'yxati (deploy'dan keyin)

```bash
docker compose exec web python manage.py check --deploy   # xavfsizlik ogohlantirishlari
docker compose exec web python manage.py migrate --check  # migratsiya yetishmovchiligi
docker compose exec web python manage.py test             # avtotestlar
```

Qo'lda tekshiring: ro'yxatdan o'tish (SMS keladi?), login, e'lon berish,
savat → checkout, admin panel (`/admin/`), chat (WebSocket).

---

## 7. 1000+ foydalanuvchi uchun scaling

Bitta `daphne` async server odatda 1000 foydalanuvchini bemalol ko'taradi.
Yuk oshsa, web'ni gorizontal kengaytiring:

```bash
docker compose up -d --scale web=3
```

> Eslatma: `--scale` bilan nginx upstream'ni DNS qayta-resolve qilishi uchun
> `nginx.conf` da `upstream` o'rniga `resolver 127.0.0.11 valid=10s;` + o'zgaruvchili
> `proxy_pass` ishlatish kerak bo'ladi. Yagona web bilan boshlang, kerak bo'lganda kengaytiring.

Boshqa tavsiyalar:
- **PostgreSQL** `max_connections` ni kuzating (CONN_MAX_AGE=60 o'rnatilgan).
- **Sentry** ni yoqing (`SENTRY_DSN`) — production xatolarini real-time ko'rasiz.
- **Backup**: `docker compose exec db pg_dump -U samcity samcity > backup.sql` (kunlik cron).
- **Media** fayllar `media_data` volume'da — uni ham backup qiling.

---

## 8. Foydali buyruqlar

```bash
docker compose ps                      # holat
docker compose logs -f web             # web loglari
docker compose restart web             # qayta yuklash
docker compose down                    # to'xtatish (ma'lumot saqlanadi)
docker compose exec web bash           # konteyner ichiga kirish
docker compose exec db pg_dump -U samcity samcity > backup_$(date +%F).sql   # baza backup
```

---

## ✅ Tuzatilgan kamchiliklar (shu sessiyada)

1. ✅ `.env.production` — to'liq production shablon (DEBUG=False, Postgres, Redis, SECRET_KEY, SMS/payment).
2. ✅ Payme webhook (`payme.py`) — `atomic + select_for_update`: parallel so'rovda ikki marta to'lashning oldi olindi.
3. ✅ Click webhook (`click.py`) — xuddi shunday qator qulfi qo'shildi.
4. ✅ `nginx.conf` — gzip siqish qo'shildi; HTTPS o'tish bo'yicha aniq izohlar.
5. ✅ HTTPS redirect-loop oldini olish — `SECURE_SSL_REDIRECT` env orqali boshqariladi.
6. ⏳ Eski fayllarni o'chirish — 2-bo'limdagi buyruq bilan o'zingiz bajaring (sandbox cheklovi).

**Allaqachon mavjud va to'g'ri bo'lgani:** Dockerfile (multi-stage, non-root), docker-compose
(postgres+redis+nginx, healthcheck), `.dockerignore`, security header'lar/HSTS/secure cookie
(DEBUG=False da), DRF throttling, checkout'da atomic+lock, health/ready endpoint'lar, JWT, CORS.
