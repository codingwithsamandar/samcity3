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
# (Supabase/S3 kaliti, ACL, region, bucket). Deploy'ni bloklamaydi (|| echo).
# `timeout` SHART: bu S3 ga tarmoq I/O qiladi va javob kelmasa cheksiz osilib,
# entrypoint'ning qolgan qismini (katalog, seed) to'sib qo'yardi.
echo "▶ Media storage tekshiruvi..."
timeout 60 python manage.py check_media \
  || echo "!! check_media xato yoki 60s timeout (yuqoriga qarang)"

# ── Yetim rasm yozuvlari (bazada bor, storage'da YO'Q) ──
# Yuqoridagi tekshiruv YANGI fayl yozib o'qiydi — u faqat "storage hozir
# ishlayaptimi?" degan savolga javob beradi va yetim yozuvlarni KO'RMAYDI.
# Ular esa foydalanuvchida singan rasm bo'lib chiqadi (topilgan misol:
# ads/2026/06/rrr.jpg — bazada AdImage bor, Supabase 404 qaytaradi).
# Har yozuv = 1 ta S3 HEAD so'rovi, shuning uchun timeout kattaroq.
# Faqat o'qiydi — hech nima o'zgartirmaydi.
echo "▶ Yetim rasm yozuvlari tekshiruvi..."
timeout 180 python manage.py check_media --rows \
  || echo "!! check_media --rows xato yoki 180s timeout (yuqoriga qarang)"

# ── Yetim yozuvlarni TUZATISH (BIR MARTALIK) ──────────────────────────────────
# Render'da FIX_ORPHAN_MEDIA=true qo'ying; deploy tugagach QAYTA false qiling.
# Doimiy yoqib qo'yish shart emas — yuqoridagi tekshiruv yetimlarni loglarda
# baribir ko'rsatib turadi, --fix esa yozuv o'chiradi.
#
# Ma'lumot yo'qotmaydi: storage javob bermasa buyruq "tekshirib bo'lmadi" deb
# o'tkazib yuboradi va HECH NIMANI o'chirmaydi. Bu ataylab sinab ko'rilgan —
# S3 uzilishi taqlid qilinganda 185 ta yozuvning hech biriga tegilmadi.
FIX_MEDIA_LC=$(printf '%s' "${FIX_ORPHAN_MEDIA:-}" | tr '[:upper:]' '[:lower:]')
if [ "$FIX_MEDIA_LC" = "true" ] || [ "$FIX_MEDIA_LC" = "1" ] || [ "$FIX_MEDIA_LC" = "yes" ]; then
  echo "════════ YETIM YOZUVLARNI TUZATISH (FIX_ORPHAN_MEDIA=$FIX_ORPHAN_MEDIA) ════════"
  timeout 180 python manage.py check_media --rows --fix \
    || echo "!! check_media --fix xato yoki 180s timeout (yuqoriga qarang)"
  echo "════════ TUGADI — endi Render'da FIX_ORPHAN_MEDIA=false qiling ════════"
fi

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

# ── Katalog tavsiya narxlari (idempotent) ──
# translate_catalog'dan KEYIN — narxlar o'zbekcha nom bo'yicha biriktiriladi.
# Faqat narxsiz (suggested_price IS NULL) yozuvlarga tegadi, admin narxlarini
# saqlaydi. Hammasi narxli bo'lsa hech narsa qilmaydi.
echo "▶ Katalog tavsiya narxlari..."
python manage.py set_catalog_prices || echo "!! set_catalog_prices xato bilan tugadi (yuqoriga qarang)"

# ── Katalog kategoriya tuzatishi (idempotent) ──
# Import'da 'Household' mos kategoriya topmagani uchun kategoriyasiz qolgan
# mahsulotlarni «Uy-ro'zg'or»ga biriktiradi. NULL qolmasa hech narsa qilmaydi.
echo "▶ Katalog kategoriya tuzatishi..."
python manage.py fix_catalog_categories || echo "!! fix_catalog_categories xato bilan tugadi (yuqoriga qarang)"

# ── Rasmsiz mahsulotlarga placeholder (idempotent) ──
# Tashqi yuklashsiz topilmagan rasmlar o'rniga toza kategoriya-rangli plitka
# (nom + bosh harflar). Faqat rasmsizlarga tegadi; rasm bo'lsa o'tkazib yuboradi.
echo "▶ Rasmsiz mahsulot placeholderlari..."
python manage.py gen_catalog_placeholders || echo "!! gen_catalog_placeholders xato bilan tugadi (yuqoriga qarang)"

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
