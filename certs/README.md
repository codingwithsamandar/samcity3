# TLS sertifikatlar (`certs/`)

Bu papkaga nginx HTTPS uchun **ikkita fayl** kerak:

- `fullchain.pem` — sertifikat zanjiri
- `privkey.pem` — maxfiy kalit

> ⚠️ Bu `.pem` fayllar git'ga **tushmaydi** (`.gitignore` da). Faqat shu README
> va `.gitkeep` saqlanadi.

> ℹ️ **Sertifikatsiz ham ishlaydi:** `nginx.conf` default holatda 80-portda
> (HTTP) ishlaydi — HTTPS bloki izohli (opt-in). Sertifikat faqat HTTPS yoqmoqchi
> bo'lsangiz kerak.

## 1. Lokal / dev — self-signed sertifikat

Loyiha root'idan:

```bash
# Linux / macOS:
bash scripts/gen-certs.sh

# Windows (PowerShell):
powershell -ExecutionPolicy Bypass -File scripts\gen-certs.ps1
```

Yoki qo'lda (openssl kerak):

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/privkey.pem -out certs/fullchain.pem \
  -subj "/C=UZ/ST=Samarqand/L=Shofirkon/O=SamCity/CN=localhost"
```

So'ng `nginx.conf` dagi HTTPS blokidagi izohlarni oching (`listen 443 ssl;` ...).

## 2. Production — Let's Encrypt (bepul, ishonchli)

```bash
sudo certbot certonly --standalone -d yourdomain.com
# Hosil bo'lgan fayllarni shu papkaga nusxalang/ulang:
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem certs/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   certs/
```
