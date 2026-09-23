#!/usr/bin/env bash
# Generate CA + server TLS certs for PostgreSQL Docker (dev/staging)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/certs/postgres"
mkdir -p "$OUT"
DAYS="${CERT_DAYS:-825}"
CN="${CERT_CN:-postgres}"

openssl req -x509 -nodes -newkey rsa:4096 -days "$DAYS" \
  -keyout "$OUT/ca.key" \
  -out "$OUT/ca.crt" \
  -subj "/CN=SEO-Autopilot-Postgres-CA/O=SEO Autopilot/C=US"

openssl req -nodes -newkey rsa:2048 \
  -keyout "$OUT/server.key" \
  -out "$OUT/server.csr" \
  -subj "/CN=${CN}/O=SEO Autopilot/C=US"

EXT="$OUT/san.cnf"
cat > "$EXT" << EXTFILE
subjectAltName=DNS:postgres,DNS:localhost,DNS:127.0.0.1,IP:127.0.0.1
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
EXTFILE

openssl x509 -req -in "$OUT/server.csr" -days "$DAYS" \
  -CA "$OUT/ca.crt" -CAkey "$OUT/ca.key" -CAcreateserial \
  -out "$OUT/server.crt" \
  -extfile "$EXT"

chmod 600 "$OUT/server.key" "$OUT/ca.key"
chmod 644 "$OUT/server.crt" "$OUT/ca.crt"
rm -f "$OUT/server.csr" "$EXT" "$OUT/ca.srl"

echo "Postgres TLS material written to $OUT:"
ls -la "$OUT"
echo ""
echo "Enable: POSTGRES_SSL=true  (see docs/POSTGRES_SSL.md)"
