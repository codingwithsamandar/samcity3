# SamCity — tezkor o'rnatish (5 ta bloker hal qilingan)

## TL;DR

```bash
# Linux / macOS
bash scripts/setup.sh

# Windows
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

So'ng: `python manage.py runserver` → http://127.0.0.1:8000

---

## Hal qilingan masalalar

### 1–2. `.env` va `DJANGO_SECRET_KEY`
- `.env` fayli yaratildi (dev uchun tayyor, generatsiya qilingan `SECRET_KEY` bilan).
- `settings.py` endi `.env` ni **avtomatik o'qiydi** (qo'shimcha paketsiz). Haqiqiy
  muhit o'zgaruvchilari ustun (docker-compose/CI ni bekor qilmaydi).
- Production: `.env` da `DJANGO_DEBUG=False` qiling va **yangi** `DJANGO_SECRET_KEY`
  qo'ying:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```

### 3. `certs/` (nginx TLS)
- `certs/` papka + hujjat qo'shildi. **nginx sertifikatsiz ham ishlaydi** (default
  80-port / HTTP; HTTPS bloki `nginx.conf` da izohli — opt-in).
- HTTPS kerak bo'lsa: `bash scripts/gen-certs.sh` (yoki `.ps1`) → self-signed
  sertifikat. Prod uchun Let's Encrypt (qarang: `certs/README.md`).

### 4. Flutter `assets/icon/`
- Papka + manba `icon.svg` + ko'rsatma qo'shildi. **Build buzilmaydi** — `flutter
  build` standart ikonka bilan ishlaydi. Maxsus ikonka uchun: SVG'ni PNG'ga
  aylantiring va generatorni ishga tushiring (`mobile/assets/icon/README.md`).

### 5. `venv/` (Windows → Linux mos emas)
- `venv/` git'ga tushmaydi (`.gitignore`). Linux/Mac serverda **qayta yarating** —
  `scripts/setup.sh` eski venv'ni o'chirib, toza o'rnatadi.

---

## Docker bilan (eng oson, to'liq stack)

```bash
cp .env.example .env   # qiymatlarni to'ldiring (POSTGRES_*, REDIS_URL, ...)
docker compose up --build
```
Bu postgres + redis + daphne (web) + nginx ni ko'taradi.
