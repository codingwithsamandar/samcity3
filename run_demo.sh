#!/usr/bin/env bash
# ============================================================
#  SamCity demo - bir buyruqli ishga tushirish (macOS / Linux)
#  Ishga tushirish:  bash run_demo.sh
# ============================================================
set -e
cd "$(dirname "$0")"

echo "============================================================"
echo "  SamCity demo tayyorlanmoqda..."
echo "============================================================"

# 1. Virtual muhit
if [ ! -d ".venv" ]; then
  echo "[1/4] Virtual muhit yaratilmoqda..."
  python3 -m venv .venv
else
  echo "[1/4] Virtual muhit mavjud."
fi
source .venv/bin/activate

# 2. Kutubxonalar
echo "[2/4] Kutubxonalar o'rnatilmoqda..."
python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt

# 3. Migratsiya + demo ma'lumotlar
echo "[3/4] Baza va demo ma'lumotlar yuklanmoqda..."
python manage.py seed_all

# 4. Server
echo ""
echo "============================================================"
echo "  Server: http://127.0.0.1:8000/"
echo "  DEMO: +998901234567 / demo1234   ADMIN: +998900000000 / admin1234"
echo "  To'xtatish: Ctrl+C"
echo "============================================================"
python manage.py runserver
