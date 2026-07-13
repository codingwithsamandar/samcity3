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

# ── Media storage tekshiruvi (yoz→o'qi→o'chir) ──
# Natija shu loglarda chiqadi: rasm/media saqlanmasa sababini aniq ko'rsatadi
# (Supabase/S3 kaliti, ACL, region, bucket). Deploy'ni bloklamaydi (|| true).
echo "▶ Media storage tekshiruvi..."
python manage.py check_media || echo "!! check_media xato bilan tugadi (yuqoriga qarang)"

# ── Markaziy katalog (avtomatik, bir martalik) ──
# Bepul tarifda Shell yo'q — katalog bo'sh bo'lsa New/ manbasidan shu yerda
# import qilinadi (import_catalog idempotent; rasm faqat yo'q bo'lsa yoziladi).
# To'lgan bazada hech narsa qilmaydi, deploy'ni bloklamaydi (|| true).
echo "▶ Markaziy katalog tekshiruvi..."
CATALOG_COUNT=$(python manage.py shell -c "from delivery.models import CatalogProduct; print(CatalogProduct.objects.count())" 2>/dev/null | tail -1)
if [ "$CATALOG_COUNT" = "0" ]; then
  echo "════════ KATALOG IMPORT BOSHLANDI (baza bo'sh) ════════"
  python manage.py import_catalog || echo "!! import_catalog xato bilan tugadi (yuqoriga qarang)"
  echo "════════ KATALOG IMPORT YAKUNLANDI ════════"
else
  echo "  Katalog: ${CATALOG_COUNT:-?} ta mahsulot — import shart emas."
fi

# ── Katalog nomlarini o'zbekchaga o'girish (idempotent) ──
# Import ma'lumotlari inglizcha; bu buyruq o'zbekchaga o'giradi. Allaqachon
# o'girilgan yozuvlarni o'tkazib yuboradi — har deploy'da xavfsiz ishlaydi.
echo "▶ Katalog tarjimasi (o'zbekcha)..."
python manage.py translate_catalog || echo "!! translate_catalog xato bilan tugadi (yuqoriga qarang)"

# ── Tuman + hokim (avtomatik, bir martalik) ──
# Hokim paneli (/hokim/) ishlashi uchun kamida bitta tuman + hokim kerak.
# Seed unga alohida ma'lumot yaratmaydi, shuning uchun tuman bo'sh bo'lsa shu
# yerda yaratamiz (idempotent; to'lgan bazada hech narsa qilmaydi).
echo "▶ Tuman/hokim tekshiruvi..."
DISTRICT_COUNT=$(python manage.py shell -c "from main.models import District; print(District.objects.count())" 2>/dev/null | tail -1)
if [ "$DISTRICT_COUNT" = "0" ]; then
  echo "════════ TUMAN/HOKIM SEED BOSHLANDI (baza bo'sh) ════════"
  python manage.py seed_districts --force || echo "!! seed_districts xato bilan tugadi (yuqoriga qarang)"
  echo "════════ TUMAN/HOKIM SEED YAKUNLANDI ════════"
else
  echo "  Tuman: ${DISTRICT_COUNT:-?} ta — seed shart emas."
fi

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
