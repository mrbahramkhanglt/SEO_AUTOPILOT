#!/usr/bin/env bash
# Basic automated penetration / security regression tests against local API
set -uo pipefail
API="${API_URL:-http://127.0.0.1:8020}"
PASS=0
FAIL=0

ok() { echo "  PASS: $1"; PASS=$((PASS+1)); }
bad() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

echo "=== Penetration tests against $API ==="

# 1. Health
code=$(curl -s -o /dev/null -w "%{http_code}" "$API/health")
[[ "$code" == "200" ]] && ok "health 200" || bad "health got $code"

# 2. Security headers
hdrs=$(curl -s -D- -o /dev/null "$API/health")
echo "$hdrs" | grep -qi "X-Content-Type-Options: nosniff" && ok "nosniff" || bad "missing nosniff"
echo "$hdrs" | grep -qi "X-Frame-Options: DENY" && ok "frame deny" || bad "missing frame deny"
echo "$hdrs" | grep -qi "Content-Security-Policy" && ok "CSP" || bad "missing CSP"

# 3. SSRF
code=$(curl -s -o /tmp/ssrf.json -w "%{http_code}" -X POST "$API/api/auth/register" \
  -H 'Content-Type: application/json' \
  -d '{"email":"pentest1@seo.ai","password":"testpass123","full_name":"PT"}')
# login for token/cookie
rm -f /tmp/pt_cookies.txt
curl -s -c /tmp/pt_cookies.txt -X POST "$API/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"pentest1@seo.ai","password":"testpass123"}' >/dev/null

code=$(curl -s -b /tmp/pt_cookies.txt -o /tmp/ssrf.json -w "%{http_code}" \
  -X POST "$API/api/websites" -H 'Content-Type: application/json' \
  -d '{"url":"http://127.0.0.1/"}')
[[ "$code" == "400" ]] && ok "SSRF blocks 127.0.0.1" || bad "SSRF 127.0.0.1 got $code $(cat /tmp/ssrf.json)"

code=$(curl -s -b /tmp/pt_cookies.txt -o /tmp/ssrf2.json -w "%{http_code}" \
  -X POST "$API/api/websites" -H 'Content-Type: application/json' \
  -d '{"url":"http://metadata.google.internal/"}')
[[ "$code" == "400" ]] && ok "SSRF blocks metadata host" || bad "SSRF metadata got $code"

# 4. Unauthenticated access to protected routes
code=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/websites")
[[ "$code" == "401" ]] && ok "websites requires auth" || bad "websites open ($code)"

code=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/admin/settings")
[[ "$code" == "401" ]] && ok "admin requires auth" || bad "admin open ($code)"

# 5. Weak password rejected
code=$(curl -s -o /tmp/weak.json -w "%{http_code}" -X POST "$API/api/auth/register" \
  -H 'Content-Type: application/json' -d '{"email":"weak@seo.ai","password":"123"}')
[[ "$code" == "400" || "$code" == "422" ]] && ok "weak password rejected" || bad "weak password accepted $code"

# 6. SQL injection on login (should not 500)
code=$(curl -s -o /tmp/sqli.json -w "%{http_code}" -X POST "$API/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin'\'' OR 1=1--","password":"x"}')
[[ "$code" == "401" || "$code" == "422" ]] && ok "SQLi login handled" || bad "SQLi login status $code"

# 7. Oversized body
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/auth/login" \
  -H 'Content-Type: application/json' \
  -H 'Content-Length: 2000000' \
  --data-binary @<(python3 -c "print('{\"email\":\"a@b.c\",\"password\":\"x\"}' + 'x'*1500000)") 2>/dev/null || echo 000)
# may be 413 or connection reset
[[ "$code" == "413" || "$code" == "400" || "$code" == "000" || "$code" == "422" || "$code" == "401" ]] && ok "large body not accepted as success" || bad "large body $code"

# 8. Cookie httpOnly on login
hdrs=$(curl -s -D- -o /tmp/login.json -X POST "$API/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"pentest1@seo.ai","password":"testpass123"}')
echo "$hdrs" | grep -qi "Set-Cookie:.*seo_access_token" && ok "Set-Cookie present" || bad "no auth cookie"
echo "$hdrs" | grep -i "Set-Cookie:" | grep -qi "HttpOnly" && ok "cookie HttpOnly" || bad "cookie not HttpOnly"

# 9. Cookie auth works without Authorization header
code=$(curl -s -b /tmp/pt_cookies.txt -o /dev/null -w "%{http_code}" "$API/api/auth/me")
[[ "$code" == "200" ]] && ok "cookie auth /me" || bad "/me with cookie $code"

# 10. Logout clears session
curl -s -b /tmp/pt_cookies.txt -c /tmp/pt_cookies.txt -X POST "$API/api/auth/logout" >/dev/null
code=$(curl -s -b /tmp/pt_cookies.txt -o /dev/null -w "%{http_code}" "$API/api/auth/me")
[[ "$code" == "401" ]] && ok "logout invalidates cookie" || bad "logout still authed $code"

# 11. Path traversal style on website id
curl -s -c /tmp/pt_cookies.txt -X POST "$API/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"pentest1@seo.ai","password":"testpass123"}' >/dev/null
code=$(curl -s -b /tmp/pt_cookies.txt -o /dev/null -w "%{http_code}" \
  "$API/api/websites/../../../etc/passwd")
[[ "$code" == "401" || "$code" == "404" || "$code" == "422" || "$code" == "405" ]] && ok "path traversal not exposed" || bad "path traversal $code"

echo ""
echo "Results: PASS=$PASS FAIL=$FAIL"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
