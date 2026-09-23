# CI/CD – SEO Autopilot AI

GitHub Actions under `.github/workflows/`.

## Pipelines

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **CI** | `ci.yml` | push/PR to `main` | Backend tests, import check, frontend build, API smoke + pentest |
| **Security** | `security-scan.yml` | push/PR, weekly cron | pip-audit, bandit, npm audit, gitleaks |
| **CD Docker** | `cd-docker.yml` | push to `main`, tags `v*` | Build & push images to **GHCR** |

## CI jobs

1. **backend-test** – `pytest`
2. **backend-lint** – ruff (advisory)
3. **frontend** – `npm install` + build
4. **api-smoke** – uvicorn, `/health` `/live` `/ready`, penetration script

## CD (container registry)

Images:

```text
ghcr.io/<owner>/seo-autopilot-backend:latest
ghcr.io/<owner>/seo-autopilot-frontend:latest
```

Requires package write permission (default `GITHUB_TOKEN` on `main`).

Optional repo variable: `NEXT_PUBLIC_API_URL` for frontend build-arg.

### Pull images

```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USER --password-stdin
docker pull ghcr.io/mrbahramkhanglt/seo-autopilot-backend:latest
```

Package visibility: GitHub → Packages → package settings (public/private).

## Secrets (optional later)

| Secret | Use |
|--------|-----|
| `GITHUB_TOKEN` | Automatic |
| Deploy keys / `SSH_KEY` | Future VPS deploy |
| `DOCKERHUB_*` | Alternate registry |

## Local equivalents

```bash
make test
API_URL=http://127.0.0.1:8000 bash scripts/penetration-test.sh
bash scripts/security-scan.sh
docker compose build
```

## Status badges (README)

```markdown
![CI](https://github.com/mrbahramkhanglt/SEO_AUTOPILOT/actions/workflows/ci.yml/badge.svg)
![Security](https://github.com/mrbahramkhanglt/SEO_AUTOPILOT/actions/workflows/security-scan.yml/badge.svg)
```
