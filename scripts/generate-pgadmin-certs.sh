#!/usr/bin/env bash
# Generate self-signed TLS certs for pgAdmin Docker (dev/staging)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/certs/pgadmin"
mkdir -p "$OUT"

DAYS="${CERT_DAYS:-825}"
CN="${CERT_CN:-localhost}"

openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$OUT/server.key" \
  -out "$OUT/server.cert" \
  -days "$DAYS" \
  -subj "/CN=${CN}/O=SEO Autopilot/C=US" \
  -addext "subjectAltName=DNS:localhost,DNS:pgadmin,IP:127.0.0.1"

chmod 600 "$OUT/server.key"
chmod 644 "$OUT/server.cert"
echo "Wrote:"
echo "  $OUT/server.cert"
echo "  $OUT/server.key"
echo "Enable TLS: set PGADMIN_ENABLE_TLS=true and restart pgadmin (see docs/PGADMIN.md)"
