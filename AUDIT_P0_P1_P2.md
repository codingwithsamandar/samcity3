# SamCity — P0/P1/P2 tayyorlik auditi

Holat belgilari: ✅ tayyor · 🔧 shu sessiyada tuzatildi

## P0 — Ishga tushirishdan oldin majburiy

| # | Talab | Holat | Dalil |
|---|-------|-------|-------|
| 1 | Telefon validatsiyasi (barcha endpoint) | 🔧 | `api/serializers.py` 9–15 raqam; `main/views.py` register; model `phone_validator` (`main/models.py:8`) |
| 2 | OTP muddati (expiry) | ✅ | `api/views.py:113` `expires_at__gt=now`; web `verify_otp` ham |
| 3 | OTP urinish limiti | ✅ | `api/views.py:119` `>=OTP_MAX_ATTEMPTS` → 429 lockout |
| 4 | JWT muddati + refresh | ✅ | `settings.py:309-311` access 60daq, refresh 30kun, `ROTATE_REFRESH_TOKENS=True`; `/auth/refresh/` |
| 5 | Lat/Lng validatsiyasi | 🔧 | taxi/booking/places avval; qo'shildi: `Ad`, `HelpRequest`, `DriverLocation`; view runtime tekshiruvi `delivery/views.py:316` |
| 6 | Reyting 1–5 | 🔧 | booking/places avval; qo'shildi: taxi `ServiceReview`/`TaxistReview` validatorlari |
| 7 | Permissionlar (user ≠ admin) | ✅ | `delivery/tests.py`, `places/tests.py` egalik testlari (begona → 302/404); admin `@staff_member_required` |
| 8 | Sirlar `.env` orqali | 🔧 | `settings.py` `.env` avto-yuklagich + `.env` (generatsiya qilingan `SECRET_KEY`) |
| 9 | DEBUG=False productionda | ✅ | `settings.py:15` env-driven; `.env` prod'da `DJANGO_DEBUG=False` |
| 10 | HTTPS majburiy | ✅ | `settings.py` `SECURE_SSL_REDIRECT`/HSTS (DEBUG=False da); `nginx.conf` 443 bloki + `certs/` |

## P1 — Kuchli tavsiya

| # | Talab | Holat | Dalil |
|---|-------|-------|-------|
| 1 | Taksi ikki marta qabul qilinmasligi | ✅ | Arxitektura: sayohat yaratilishda muayyan taksistga bog'lanadi (yo'lovchi tanlaydi) — qabul oqimi yo'q |
| 2 | Delivery race condition | 🔧 | `order_accept` `select_for_update` bilan atomik (`delivery/views.py`); checkout oversell avval `select_for_update` (`:183`) |
| 3 | Chat WS qayta ulanish | ✅ | `neighborhood_chat_room.html:207` `onclose→reconnect`; `order_track.html` auto-reconnect |
| 4 | Notification yo'qolmasligi | ✅ | DB'da saqlanadi (`notifications.Notification`), WS faqat signal; o'qilmaganlar bazada qoladi |
| 5 | Postgres indekslari | ✅ | Kompozit indekslar: `Order`/`Trip`/`VenueBooking` + status/category `db_index` |
| 6 | Fayl hajm/format cheklovi | ✅ | `main/utils.py` whitelist (.jpg/.png/.webp/...) + 5MB limit |
| 7 | Spam/flood himoyasi | ✅ | `@ratelimit` (register 5/soat, otp, chat); DRF throttle scope'lari |
| 8 | Admin audit loglari | ✅ | Django admin `LogEntry` (avtomatik); `shofirkon.security` logger (OTP/login) |

## P2 — O'sish uchun

| # | Talab | Holat | Dalil |
|---|-------|-------|-------|
| 1 | Monitoring (Sentry/log) | ✅ | `settings.py` Sentry (SENTRY_DSN bo'lsa) + LOGGING |
| 2 | Backup/restore rejasi | ⚠️ hujjat | Quyida — qo'lda qadamlar |

### Backup/restore (qisqa reja)
```bash
# Backup (Postgres):
docker compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%F).sql
# Restore:
docker compose exec -T db psql -U $POSTGRES_USER $POSTGRES_DB < backup_YYYY-MM-DD.sql
# Media fayllar: media/ papkasini ham nusxalang (rsync/S3).
```
Avtomatik kunlik backup uchun cron yoki managed DB snapshot tavsiya etiladi.

---

## Shu sessiyada tuzatilganlar (test bilan)
- `order_accept` race-himoyasi → `delivery/tests.py::OrderAcceptRaceTests`
- Telefon/lat-lng/reyting validatsiyasi → `api/tests_validation.py`
