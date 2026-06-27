#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  SamCity — repozitoriya tozalash (Linux/macOS)
#  Ishlatish:  loyiha papkasida →  bash cleanup.sh
#
#  venv/, db.sqlite3, .env, .env.production, __pycache__, eski log/skript
#  fayllarni o'chiradi; git kuzatuvidan chiqaradi; hisobotlarni docs/ ga ko'chiradi.
#  .env.example saqlanadi.
# ═══════════════════════════════════════════════════════════════════
set -e
echo "SamCity tozalash boshlandi..."

PATHS=(venv db.sqlite3 .env .env.production \
       errors.txt check.txt urls.txt \
       find_urls.py replace_urls.py test_templates.py)

# git repo bo'lsa — kuzatuvdan chiqaramiz
if [ -d .git ]; then
  for p in "${PATHS[@]}"; do git rm -r --cached --ignore-unmatch "$p" >/dev/null 2>&1 || true; done
  find . -type d -name __pycache__ -exec git rm -r --cached --ignore-unmatch {} + >/dev/null 2>&1 || true
  echo "  git kuzatuvidan chiqarildi."
fi

# Jismonan o'chirish
for p in "${PATHS[@]}"; do
  if [ -e "$p" ]; then rm -rf "$p"; echo "  o'chirildi: $p"; fi
done
find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -delete 2>/dev/null || true

# Hisobot/audit fayllarini docs/ ga
mkdir -p docs
for d in AUDIT_NATIJA.md PRODUCTION_AUDIT.md SAYT_TEKSHIRUV.md \
         SAVAT_REJASI.md PHASES_1-7_REPORT.md SECURITY_AUDIT.md README.txt; do
  if [ -f "$d" ]; then mv -f "$d" docs/; echo "  docs/ ga: $d"; fi
done

echo ""
echo "Tayyor! Endi commit qiling:"
echo '  git add -A && git commit -m "chore: repo tozalash (venv/.env/db olib tashlandi, docs/)"'
echo ""
echo "ESLATMA: agar eski SECRET_KEY GitHub'ga chiqqan bo'lsa, uni ALMASHTIRING."
