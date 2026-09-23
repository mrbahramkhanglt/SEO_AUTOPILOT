# Automated vulnerability scanning

## Local

```bash
bash scripts/security-scan.sh
```

Reports are written to `security-reports/`:

| File | Tool |
|------|------|
| `pip-audit.txt` / `.json` | Python deps (OSV/PyPI) |
| `bandit.txt` / `.json` | Python SAST |
| `npm-audit.txt` / `.json` | Frontend deps |
| `ruff-security.txt` | Ruff S/B rules |
| `trivy.txt` | Optional filesystem/container (if trivy installed) |

Exit code **1** if pip-audit, bandit, or npm audit (high+) fails.

## CI (GitHub Actions)

Workflow: `.github/workflows/security-scan.yml`

Triggers: push/PR to main, weekly cron, manual dispatch.

Jobs:
1. **pip-audit** on `backend/requirements.txt`
2. **bandit** on `backend/app`
3. **npm audit --audit-level=high**
4. **gitleaks** secret scan

## Manual commands

```bash
# Backend
cd backend
pip install pip-audit "bandit[toml]"
pip-audit -r requirements.txt
bandit -r app -ll -ii -x app/tests

# Frontend
cd frontend
npm audit --audit-level=high
```

## Policy

- Fix **Critical/High** before release
- Medium: track in issues within 30 days
- Never commit secrets; gitleaks enforces on CI
