@echo off
REM ============================================================
REM  SamCity demo - bir tugmali ishga tushirish (Windows)
REM  Ikki marta bosing yoki: run_demo.bat
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo   SamCity demo tayyorlanmoqda...
echo ============================================================
echo.

REM --- 1. Virtual muhit ---
if not exist ".venv\" (
    echo [1/4] Virtual muhit yaratilmoqda...
    python -m venv .venv
) else (
    echo [1/4] Virtual muhit mavjud, o'tkazib yuborildi.
)
call ".venv\Scripts\activate.bat"

REM --- 2. Kutubxonalar ---
echo [2/4] Kutubxonalar o'rnatilmoqda (bir oz vaqt olishi mumkin)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt

REM --- 3. Migratsiya + demo ma'lumotlar ---
echo [3/4] Baza va demo ma'lumotlar yuklanmoqda...
python manage.py seed_all

REM --- 4. Server ---
echo.
echo ============================================================
echo   Server ishga tushmoqda: http://127.0.0.1:8000/
echo.
echo   DEMO HISOBLAR (parol: demo1234):
echo     +998901234567  Sardor Aliyev      [user]
echo     +998903456789  Bobur Karimov      [business]
echo     +998905678901  Jasur Toshmatov    [driver]
echo   ADMIN: +998900000000  (parol: admin1234)  ->  /admin/
echo.
echo   To'xtatish uchun: Ctrl+C
echo ============================================================
echo.
python manage.py runserver

endlocal
