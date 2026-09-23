# Backend security

## Controls
- **Passwords:** bcrypt cost 12; min 8 chars; ≥2 character classes
- **JWT:** HS256, `exp`+`iat`+`iss` required; 24h default TTL; type claim
- **Auth rate limit:** 15 req/min/IP on `/api/auth/*`
- **Body limit:** 1 MB default
- **Headers:** nosniff, DENY frame, CSP, no-store; HSTS in production
- **CORS:** explicit origins only (no `*` when list set)
- **TrustedHost** in production
- **Docs disabled** when `APP_ENV=production` and `DISABLE_DOCS_IN_PRODUCTION=true`
- **SSRF:** block private IPs, link-local, cloud metadata hostnames, userinfo in URL
- **Errors:** generic 500 in production; validation errors structured
- **Audit:** register / login / login_failed logged with IP + UA
- **Startup:** refuses weak `SECRET_KEY` in production

## Ops checklist
1. `SECRET_KEY=$(openssl rand -hex 32)`
2. `APP_ENV=production`
3. `CORS_ORIGINS=https://your-frontend`
4. `ALLOWED_HOSTS=api.yourdomain.com`
5. TLS at reverse proxy
6. Rotate GitHub/Google tokens; never commit secrets

## Session storage (browser)

- **Primary:** `httpOnly` cookie `seo_access_token` (not accessible to JavaScript)
- **Flags:** `HttpOnly`, `SameSite=Lax` (or Strict), `Secure` in production
- Frontend uses `credentials: "include"` — **no localStorage/sessionStorage tokens**
- Logout: `POST /api/auth/logout` clears cookie
- API clients may still read `access_token` from JSON body if needed

## Platform admin bootstrap

Set server-side only (never in frontend env):

```bash
export ADMIN_EMAIL=admin@yourdomain.com
export ADMIN_PASSWORD='StrongPass1!'
```

Created on API startup if missing. Use a real email domain (not `.local` — validators reject reserved names).

## Penetration tests

```bash
API_URL=http://127.0.0.1:8000 bash scripts/penetration-test.sh
```

Covers: headers, SSRF, auth gates, weak passwords, SQLi handling, cookie HttpOnly, logout, path traversal.
