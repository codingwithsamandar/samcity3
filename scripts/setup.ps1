# SamCity — lokal muhitni TOZA o'rnatish (Windows PowerShell).
# Ishlatish: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "* 1/5  Eski venv'ni tozalash..."
if (Test-Path venv)  { Remove-Item -Recurse -Force venv }
if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }

Write-Host "* 2/5  Yangi virtual muhit..."
python -m venv venv
& .\venv\Scripts\Activate.ps1

Write-Host "* 3/5  Bog'liqliklar..."
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "* 4/5  .env (yo'q bo'lsa namunadan)..."
if (-not (Test-Path .env)) { Copy-Item .env.example .env }

Write-Host "* 5/5  Migratsiya + statik fayllar..."
python manage.py migrate
python manage.py collectstatic --noinput

Write-Host ""
Write-Host "OK. Ishga tushirish:"
Write-Host "   .\venv\Scripts\Activate.ps1"
Write-Host "   python manage.py runserver"
Write-Host "   python manage.py createsuperuser"
