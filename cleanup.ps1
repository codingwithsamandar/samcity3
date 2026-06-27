# ═══════════════════════════════════════════════════════════════════
#  SamCity — repozitoriya tozalash (Windows PowerShell)
#  Ishlatish:  loyiha papkasida →  powershell -ExecutionPolicy Bypass -File cleanup.ps1
#
#  Nima qiladi:
#   1. venv/, db.sqlite3, .env, .env.production, __pycache__, eski log/skript
#      fayllarni JISMONAN o'chiradi.
#   2. Agar git repo bo'lsa — ularni git kuzatuvidan ham chiqaradi (--cached).
#   3. Audit/hisobot .md fayllarini docs/ papkasiga ko'chiradi.
#  .env.example saqlanadi (bu namuna, maxfiy emas).
# ═══════════════════════════════════════════════════════════════════
$ErrorActionPreference = 'SilentlyContinue'
Write-Host "SamCity tozalash boshlandi..." -ForegroundColor Cyan

# ── 1. Katta / maxfiy / keraksiz narsalar ──
$paths = @('venv', 'db.sqlite3', '.env', '.env.production',
           'errors.txt', 'check.txt', 'urls.txt',
           'find_urls.py', 'replace_urls.py', 'test_templates.py')

# git repo bo'lsa — avval kuzatuvdan chiqaramiz (fayl diskda qoladi)
$isGit = Test-Path '.git'
if ($isGit) {
    foreach ($p in $paths) { git rm -r --cached --ignore-unmatch $p | Out-Null }
    git rm -r --cached --ignore-unmatch '__pycache__' '*/__pycache__' | Out-Null
    Write-Host "  git kuzatuvidan chiqarildi." -ForegroundColor Green
}

# Jismonan o'chirish
foreach ($p in $paths) {
    if (Test-Path $p) { Remove-Item -Recurse -Force $p; Write-Host "  o'chirildi: $p" -ForegroundColor Yellow }
}
# Barcha __pycache__ papkalari
Get-ChildItem -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Include '*.pyc' | Remove-Item -Force

# ── 2. Hisobot/audit fayllarini docs/ ga ko'chirish ──
if (-not (Test-Path 'docs')) { New-Item -ItemType Directory -Path 'docs' | Out-Null }
$docs = @('AUDIT_NATIJA.md', 'PRODUCTION_AUDIT.md', 'SAYT_TEKSHIRUV.md',
          'SAVAT_REJASI.md', 'PHASES_1-7_REPORT.md', 'SECURITY_AUDIT.md', 'README.txt')
foreach ($d in $docs) {
    if (Test-Path $d) { Move-Item -Force $d "docs\"; Write-Host "  docs/ ga: $d" -ForegroundColor Green }
}

Write-Host ""
Write-Host "Tayyor! Endi git'da commit qiling:" -ForegroundColor Cyan
Write-Host '  git add -A && git commit -m "chore: repo tozalash (venv/.env/db olib tashlandi, docs/)"'
Write-Host ""
Write-Host "ESLATMA: agar eski SECRET_KEY GitHub'ga chiqqan bo'lsa, uni ALMASHTIRING." -ForegroundColor Red
