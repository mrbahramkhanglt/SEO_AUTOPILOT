#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$ROOT/backend:${PYTHONPATH:-}"
export PATH="${HOME}/.local/bin:$PATH"

cd "$ROOT/backend"
pip3 install --user -q -r requirements.txt
python3 -c "import asyncio; from app.database.session import init_db; asyncio.run(init_db())"
echo "Starting API on :8000 ..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

if command -v npm >/dev/null 2>&1; then
  cd "$ROOT/frontend"
  if [ ! -d node_modules ]; then npm install; fi
  echo "Starting frontend on :3000 ..."
  npm run dev &
  FE_PID=$!
fi

echo "Backend PID $API_PID"
echo "API docs: http://127.0.0.1:8000/docs"
wait
