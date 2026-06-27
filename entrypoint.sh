#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  SamCity — konteyner entrypoint: migrate → collectstatic → daphne
# ═══════════════════════════════════════════════════════════════════
set -e

echo "▶ Ma'lumotlar bazasi migratsiyalari..."
python manage.py migrate --noinput

# ── Superuser'ni avtomatik yaratish (bepul tarifda Shell yo'q) ──
# DJANGO_SUPERUSER_PHONE va DJANGO_SUPERUSER_PASSWORD env'lari bo'lsa yaratadi.
# Foydalanuvchi allaqachon bo'lsa xato bermaydi ('|| true' — idempotent).
if [ -n "$DJANGO_SUPERUSER_PHONE" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "▶ Superuser tekshirilmoqda/yaratilmoqda ($DJANGO_SUPERUSER_PHONE)..."
  python manage.py createsuperuser --noinput --phone "$DJANGO_SUPERUSER_PHONE" || true
fi

# Statik fayllar build vaqtida yig'ilgan, lekin volume bo'lsa qayta yig'amiz
echo "▶ Statik fayllar..."
python manage.py collectstatic --noinput --no-post-process 2>/dev/null || \
python manage.py collectstatic --noinput 2>/dev/null || true

echo "▶ Daphne (ASGI) ishga tushmoqda :${PORT:-8000} ..."
# WebSocket (chat/taxi/delivery) uchun ASGI server — gunicorn emas, daphne
exec daphne -b 0.0.0.0 -p "${PORT:-8000}" sdev.asgi:application
