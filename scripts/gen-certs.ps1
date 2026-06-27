# SamCity — lokal self-signed TLS sertifikat (dev). Windows PowerShell.
# Ishlatish: powershell -ExecutionPolicy Bypass -File scripts\gen-certs.ps1
$ErrorActionPreference = "Stop"

$certDir = Join-Path (Split-Path $PSScriptRoot -Parent) "certs"
New-Item -ItemType Directory -Force -Path $certDir | Out-Null

$openssl = Get-Command openssl -ErrorAction SilentlyContinue
if (-not $openssl) {
    Write-Error "openssl topilmadi. Git for Windows bilan keladi yoki alohida o'rnating."
    exit 1
}

& openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
    -keyout (Join-Path $certDir "privkey.pem") `
    -out    (Join-Path $certDir "fullchain.pem") `
    -subj "/C=UZ/ST=Samarqand/L=Shofirkon/O=SamCity/CN=localhost"

Write-Host "✅ Tayyor: $certDir\fullchain.pem va $certDir\privkey.pem"
Write-Host "   Endi nginx.conf dagi HTTPS blokini oching (listen 443 ssl)."
