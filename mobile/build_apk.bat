@echo off
REM ── SamCity mobil ilova — APK yasash skripti (Windows) ──
REM Ishlatish: shu faylni ikki marta bosing yoki terminalda: build_apk.bat
cd /d %~dp0

echo.
echo ============================================
echo   SamCity APK yasash
echo ============================================
echo.
echo Telefoningiz va kompyuter BIR XIL WiFi'da bo'lishi shart.
echo Kompyuter IP manzilini bilish uchun yangi oynada "ipconfig" yozing
echo va "IPv4 Address" qiymatini oling (masalan 192.168.1.5).
echo.
set /p IP="Kompyuter IP manzili: "

echo.
echo [1/2] Paketlar yuklanmoqda...
call flutter pub get
if errorlevel 1 goto :err

echo.
echo [2/2] APK yasalmoqda (release)...
call flutter build apk --release --dart-define=API_BASE=http://%IP%:8000/api
if errorlevel 1 goto :err

echo.
echo ============================================
echo   TAYYOR!
echo   APK fayl:
echo   %~dp0build\app\outputs\flutter-apk\app-release.apk
echo ============================================
echo.
echo Shu faylni telefoningizga ko'chiring va o'rnating.
echo Server ishlab turishi kerak:  python manage.py runserver 0.0.0.0:8000
echo.
pause
exit /b 0

:err
echo.
echo XATOLIK yuz berdi. "flutter doctor" buyrug'i bilan tekshiring.
pause
exit /b 1
