#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
export PYTHONPATH="${ROOT}/backend:${PYTHONPATH:-}"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  sed -i "s/change-me-in-production-use-openssl-rand-hex-32/$(openssl rand -hex 32)/" .env || true
fi
set -a
# shellcheck disable=SC1091
source .env 2>/dev/null || true
set +a

pip3 install --user -q -r backend/requirements.txt
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:////tmp/seo_autopilot.db}"
export SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"
export ADMIN_EMAIL="${ADMIN_EMAIL:-admin@example.com}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-AdminSecure1!}"

python3 -c "from app.core.config import get_settings; get_settings.cache_clear()" 2>/dev/null || true
echo "Starting API on :8000 ..."
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
