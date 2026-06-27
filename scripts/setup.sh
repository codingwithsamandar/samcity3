#!/usr/bin/env bash
# SamCity — lokal muhitni TOZA o'rnatish (Linux / macOS).
# Windows'da yaratilgan venv/ Linux'da ishlamaydi — shuning uchun qayta yaratamiz.
# Ishlatish: bash scripts/setup.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "▶ 1/5  Eski venv'ni tozalash (agar bo'lsa)..."
rm -rf venv .venv

echo "▶ 2/5  Yangi virtual muhit..."
python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate

echo "▶ 3/5  Bog'liqliklar..."
pip install --upgrade pip
pip install -r requirements.txt

echo "▶ 4/5  .env (yo'q bo'lsa namunadan)..."
[ -f .env ] || cp .env.example .env

echo "▶ 5/5  Migratsiya + statik fayllar..."
python manage.py migrate
python manage.py collectstatic --noinput

echo ""
echo "✅ Tayyor. Ishga tushirish:"
echo "   source venv/bin/activate"
echo "   python manage.py runserver        # oddiy"
echo "   daphne -b 0.0.0.0 -p 8000 sdev.asgi:application   # WebSocket bilan"
echo "   python manage.py createsuperuser  # admin uchun"
