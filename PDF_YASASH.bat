@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo   SamCity Investor Deck - PDF yasalmoqda...
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    py make_deck_pdf.py
    goto done
)

where python >nul 2>&1
if %errorlevel%==0 (
    python make_deck_pdf.py
    goto done
)

echo   XATO: Python topilmadi.
echo   Python o'rnating: https://www.python.org/downloads/
echo.

:done
pause
