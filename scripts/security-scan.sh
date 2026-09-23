#!/usr/bin/env bash
# Automated vulnerability scanning for SEO Autopilot AI
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_DIR="${ROOT}/security-reports"
mkdir -p "$REPORT_DIR"
export PATH="${HOME}/.local/bin:${PATH}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass=0
fail=0
warn=0

section() { echo -e "\n${YELLOW}=== $1 ===${NC}"; }

run_pip_audit() {
  section "Python dependency audit (pip-audit)"
  cd "$ROOT/backend"
  python3 -m pip install -q --user pip-audit 2>/dev/null || true
  python3 -m pip install -q --user -r requirements.txt 2>/dev/null || true

  set +e
  # Prefer requirements file; fall back to local site-packages if temp venv fails (no ensurepip)
  python3 -m pip_audit -r requirements.txt --desc on --progress-spinner off \
    --format json -o "${REPORT_DIR}/pip-audit.json" 2>"${REPORT_DIR}/pip-audit.err"
  rc=$?
  if [[ $rc -ne 0 ]] && grep -q "ensurepip\|virtual environment" "${REPORT_DIR}/pip-audit.err" 2>/dev/null; then
    echo "Falling back to --path site-packages audit..."
    SITE=$(python3 -c "import site; print(site.getusersitepackages())")
    python3 -m pip_audit --path "$SITE" --desc on --progress-spinner off \
      2>&1 | tee "${REPORT_DIR}/pip-audit.txt"
    rc=${PIPESTATUS[0]}
  else
    python3 -m pip_audit -r requirements.txt --desc on --progress-spinner off \
      2>&1 | tee "${REPORT_DIR}/pip-audit.txt"
    rc=${PIPESTATUS[0]}
  fi
  set -e
  if [[ $rc -eq 0 ]]; then
    echo -e "${GREEN}pip-audit: no known vulnerabilities${NC}"
    pass=$((pass + 1))
  else
    echo -e "${RED}pip-audit: vulnerabilities found${NC}"
    fail=$((fail + 1))
  fi
}

run_bandit() {
  section "Python SAST (bandit)"
  cd "$ROOT/backend"
  python3 -m pip install -q --user "bandit[toml]" 2>/dev/null || true
  set +e
  python3 -m bandit -r app -ll -ii -x app/tests \
    -f json -o "${REPORT_DIR}/bandit.json" >/dev/null 2>&1
  python3 -m bandit -r app -ll -ii -x app/tests 2>&1 | tee "${REPORT_DIR}/bandit.txt"
  rc=${PIPESTATUS[0]}
  set -e
  if [[ $rc -eq 0 ]]; then
    echo -e "${GREEN}bandit: no medium/high issues${NC}"
    pass=$((pass + 1))
  else
    echo -e "${RED}bandit: medium/high issues found${NC}"
    fail=$((fail + 1))
  fi
}

run_npm_audit() {
  section "Frontend dependency audit (npm audit)"
  cd "$ROOT/frontend"
  if ! command -v npm >/dev/null 2>&1; then
    echo -e "${YELLOW}npm not installed — skip${NC}"
    warn=$((warn + 1))
    return
  fi
  if [[ ! -d node_modules ]]; then
    npm install 2>/dev/null || true
  fi
  set +e
  npm audit --json > "${REPORT_DIR}/npm-audit.json" 2>/dev/null
  npm audit --audit-level=high 2>&1 | tee "${REPORT_DIR}/npm-audit.txt"
  rc=${PIPESTATUS[0]}
  set -e
  if [[ $rc -eq 0 ]]; then
    echo -e "${GREEN}npm audit: no high+ vulnerabilities${NC}"
    pass=$((pass + 1))
  else
    echo -e "${RED}npm audit: high+ issues found${NC}"
    fail=$((fail + 1))
  fi
}

run_ruff_security() {
  section "Ruff security rules (S,B)"
  cd "$ROOT/backend"
  python3 -m pip install -q --user ruff 2>/dev/null || true
  set +e
  python3 -m ruff check app --select S,B --no-cache 2>&1 | tee "${REPORT_DIR}/ruff-security.txt"
  rc=${PIPESTATUS[0]}
  set -e
  if [[ $rc -eq 0 ]]; then
    echo -e "${GREEN}ruff S/B: clean${NC}"
    pass=$((pass + 1))
  else
    echo -e "${YELLOW}ruff findings (hygiene, non-blocking)${NC}"
    warn=$((warn + 1))
  fi
}

run_trivy() {
  section "Container/filesystem (trivy — optional)"
  if ! command -v trivy >/dev/null 2>&1; then
    echo -e "${YELLOW}trivy not installed — skip${NC}"
    warn=$((warn + 1))
    return
  fi
  set +e
  trivy fs --severity --scanners vuln,secret,misconfig \
    --severity-exit-code 1 \
    --format table -o "${REPORT_DIR}/trivy.txt" "$ROOT"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    echo -e "${GREEN}trivy: no HIGH/CRITICAL${NC}"
    pass=$((pass + 1))
  else
    echo -e "${RED}trivy: HIGH/CRITICAL found${NC}"
    fail=$((fail + 1))
  fi
}

echo "SEO Autopilot AI — security scan"
echo "Reports → $REPORT_DIR"
run_pip_audit
run_bandit
run_npm_audit
run_ruff_security
run_trivy

section "Summary"
echo -e "Passed: ${GREEN}${pass}${NC}  Failed: ${RED}${fail}${NC}  Warnings: ${YELLOW}${warn}${NC}"
if [[ $fail -gt 0 ]]; then
  echo -e "${RED}Security scan FAILED${NC}"
  exit 1
fi
echo -e "${GREEN}Security scan PASSED (warnings allowed)${NC}"
exit 0
