# Postgres Docker setup – SEO Autopilot AI

SQLite is the zero-config default. Use **PostgreSQL 16** for production or multi-user local work.

## Prerequisites

- Docker Engine + Docker Compose v2
- Ports free: `5432` (Postgres), `8000` (API), `3000` (frontend)

## 1. Environment file

```bash
cd seo-autopilot-ai
cp .env.example .env
```

Edit `.env` (minimum for Postgres):

```bash
SECRET_KEY=$(openssl rand -hex 32)
APP_ENV=production
APP_DEBUG=false

POSTGRES_USER=seo
POSTGRES_PASSWORD=seo_change_me
POSTGRES_DB=seo_autopilot
POSTGRES_PORT=5432

# Host machine → local backend (not inside Docker network)
DATABASE_URL=postgresql+asyncpg://seo:seo_change_me@localhost:5432/seo_autopilot

# Optional platform admin (created on API startup)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=AdminSecure1!

CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

**Async driver:** always use `postgresql+asyncpg://...` for the FastAPI app.

| Context | Host in DATABASE_URL |
|---------|----------------------|
| Backend on host, Postgres in Docker | `localhost` |
| Backend container `backend-pg` | `postgres` (service name) |

## 2. Start Postgres only

```bash
docker compose --profile postgres up -d postgres
```

Check:

```bash
docker compose --profile postgres ps
docker compose --profile postgres exec postgres pg_isready -U seo -d seo_autopilot
```

## 3A. Full stack with Postgres (Docker)

Runs `postgres` + `backend-pg` (API wired to Postgres service):

```bash
docker compose --profile postgres up --build -d postgres backend-pg frontend
```

- API: http://localhost:8000/docs  
- App: http://localhost:3000  
- Tables are created automatically on API startup (`init_db`)

> Do **not** start both `backend` and `backend-pg` (same port 8000).

## 3B. Postgres in Docker, API on host

```bash
docker compose --profile postgres up -d postgres

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL=postgresql+asyncpg://seo:seo_change_me@localhost:5432/seo_autopilot
export SECRET_KEY=$(openssl rand -hex 32)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 4. Verify connection

```bash
# Health (includes DB ping)
curl -s http://localhost:8000/health

# From host with psql client (optional)
docker compose --profile postgres exec postgres \
  psql -U seo -d seo_autopilot -c '\dt'
```

## 5. Useful commands

```bash
# Logs
docker compose --profile postgres logs -f postgres
docker compose --profile postgres logs -f backend-pg

# Stop
docker compose --profile postgres down

# Stop + delete DB volume (destructive)
docker compose --profile postgres down -v
```

## 6. Migrations (Alembic)

App also runs `create_all` on startup for MVP. For controlled schema changes:

```bash
cd backend
export DATABASE_URL=postgresql+asyncpg://seo:seo_change_me@localhost:5432/seo_autopilot
# alembic revision --autogenerate -m "description"
# alembic upgrade head
```

Ensure `alembic.ini` / `env.py` use the same `DATABASE_URL`.

## 7. Production notes

| Item | Guidance |
|------|----------|
| Password | Strong `POSTGRES_PASSWORD`; never commit `.env` |
| SECRET_KEY | `openssl rand -hex 32` |
| COOKIE_SECURE | `true` behind HTTPS |
| Backups | `pg_dump` on a schedule; keep volume snapshots |
| Managed DB | Point `DATABASE_URL` at RDS/Cloud SQL; drop local `postgres` service |
| Network | Do not publish `5432` publicly in production; use internal Docker/VPC only |

### Example `pg_dump` backup

```bash
docker compose --profile postgres exec -T postgres \
  pg_dump -U seo seo_autopilot > backup_$(date +%F).sql
```

### Restore

```bash
cat backup_2026-09-21.sql | docker compose --profile postgres exec -T postgres \
  psql -U seo -d seo_autopilot
```

## 8. Switch back to SQLite

```bash
# Stop postgres profile services
docker compose --profile postgres down

# Default compose (no profile) uses SQLite file volume
unset DATABASE_URL   # or set sqlite URL in .env
docker compose up --build backend frontend
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `connection refused` localhost:5432 | Postgres not up / wrong port / profile not enabled |
| `password authentication failed` | Match user/password in URL and `POSTGRES_*` |
| Port 5432 busy | Set `POSTGRES_PORT=5433` and use that in URL |
| API healthy but empty schema | Check logs for `init_db` / startup errors |
| `asyncpg` missing | `pip install asyncpg` (in `requirements.txt`) |


## pgAdmin

Web UI for this Postgres instance:

```bash
docker compose --profile postgres up -d postgres pgadmin
```

Open http://localhost:5050 — full steps in [PGADMIN.md](./PGADMIN.md).


## SSL/TLS

```bash
bash scripts/generate-postgres-certs.sh
# .env: POSTGRES_SSL=true
# DATABASE_URL=...\?ssl=require
docker compose --profile postgres up -d --force-recreate postgres
```

Full guide: [POSTGRES_SSL.md](./POSTGRES_SSL.md).
