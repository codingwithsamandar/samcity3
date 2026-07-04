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

# ── Daphne'ni AVVAL ishga tushiramiz (sog'liq tekshiruvi darhol o'tadi) ──
# WebSocket (chat/taxi/delivery) uchun ASGI server — gunicorn emas, daphne
echo "▶ Daphne (ASGI) ishga tushmoqda :${PORT:-8000} ..."
daphne -b 0.0.0.0 -p "${PORT:-8000}" sdev.asgi:application &
DAPHNE_PID=$!
# To'xtatishda daphne'ga signal uzatamiz (Render redeploy'da toza yopilish uchun)
trap 'kill -TERM "$DAPHNE_PID" 2>/dev/null' TERM INT

# ── Demo ma'lumotlar (bir martalik) ──
# SEED_DEMO true/TRUE/1/yes bo'lsa — daphne ishlab turgan holda demo seed qilinadi
# (loglarda ko'rinadi). Idempotent. Bir marta ishlatgach Render'da SEED_DEMO=false qiling.
# Katta-kichik harfga sezgir emas (TRUE/True/true/1/yes).
SEED_DEMO_LC=$(printf '%s' "${SEED_DEMO:-}" | tr '[:upper:]' '[:lower:]')
if [ "$SEED_DEMO_LC" = "true" ] || [ "$SEED_DEMO_LC" = "1" ] || [ "$SEED_DEMO_LC" = "yes" ]; then
  echo "════════ DEMO SEED BOSHLANDI (SEED_DEMO=$SEED_DEMO) ════════"
  python manage.py seed_all || echo "!! seed_all xato bilan tugadi (yuqoriga qarang)"
  echo "════════ DEMO SEED YAKUNLANDI ════════"
fi

# Konteynerni daphne bilan tirik ushlab turamiz
wait "$DAPHNE_PID"
