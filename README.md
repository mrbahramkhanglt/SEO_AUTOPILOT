# SEO Autopilot AI

![CI](https://github.com/mrbahramkhanglt/SEO_AUTOPILOT/actions/workflows/ci.yml/badge.svg)
![Security](https://github.com/mrbahramkhanglt/SEO_AUTOPILOT/actions/workflows/security-scan.yml/badge.svg)
![CD](https://github.com/mrbahramkhanglt/SEO_AUTOPILOT/actions/workflows/cd-docker.yml/badge.svg)


**Autonomous AI SEO Operating System**

Enter a website URL → crawl, audit, analyze, optimize, monitor.  
Potential SEO improvement only — rankings are never guaranteed.

## Quick start (local, zero Docker DB)

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (other terminal)
cd frontend
npm install
npm run dev
```

- API: http://localhost:8000/docs  
- App: http://localhost:3000  
- Default DB: SQLite (`/tmp/seo_autopilot.db`) — tables auto-create on startup

Or: `bash scripts/start-dev.sh`

## Docker (backend + frontend)

```bash
cp .env.example .env
# set SECRET_KEY for production
docker compose up --build
```

Postgres optional: `docker compose --profile postgres up`

## User flow (automatic)

1. Enter URL on homepage → register/login if needed  
2. Website onboarded  
3. **Crawl starts automatically**  
4. Score, issues, keywords, recommendations, autofix ZIP  
5. Admin: `/dashboard/admin`  
6. Approvals: `…/changes` API  

## Production checklist

| Item | Action |
|------|--------|
| `SECRET_KEY` | Strong random value |
| `APP_ENV=production` | Disables debug |
| `DATABASE_URL` | Postgres recommended at scale |
| `CORS_ORIGINS` | Your frontend origin only |
| HTTPS | Terminate TLS at proxy |
| Backups | DB volume / managed Postgres |

## Stack

- **Backend:** FastAPI, SQLAlchemy async, agents pipeline  
- **Frontend:** Next.js App Router, Tailwind  
- **Integrations:** GitHub, Netlify, Vercel, GSC, GA4, WordPress  

## Safety

- SSRF protection on crawler  
- No ranking guarantees in copy  
- Change approval workflow  
- WordPress meta dry-run + conflict detection  

## License

Proprietary — all rights reserved.

## Security tests

```bash
bash scripts/security-scan.sh
API_URL=http://127.0.0.1:8000 bash scripts/penetration-test.sh
```


## PostgreSQL

See [docs/POSTGRES.md](docs/POSTGRES.md) for Docker Compose setup.


## pgAdmin

See [docs/PGADMIN.md](docs/PGADMIN.md).


## CI/CD

See [docs/CICD.md](docs/CICD.md).
