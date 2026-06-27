#!/usr/bin/env bash
# SamCity — lokal self-signed TLS sertifikat (dev). Linux / macOS.
# Ishlatish: bash scripts/gen-certs.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/certs"
mkdir -p "$DIR"

if ! command -v openssl >/dev/null 2>&1; then
  echo "Xato: openssl topilmadi. Avval o'rnating." >&2
  exit 1
fi

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$DIR/privkey.pem" \
  -out    "$DIR/fullchain.pem" \
  -subj "/C=UZ/ST=Samarqand/L=Shofirkon/O=SamCity/CN=localhost"

echo "✅ Tayyor: $DIR/fullchain.pem va $DIR/privkey.pem"
echo "   Endi nginx.conf dagi HTTPS blokini oching (listen 443 ssl)."
