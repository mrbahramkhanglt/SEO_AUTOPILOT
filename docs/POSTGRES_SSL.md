# PostgreSQL SSL/TLS – SEO Autopilot AI

Encrypt client connections to Postgres (Docker). Separate from [pgAdmin UI HTTPS](./PGADMIN.md).

## 1. Generate certificates

```bash
bash scripts/generate-postgres-certs.sh
```

Creates under `certs/postgres/`:

| File | Role |
|------|------|
| `ca.crt` / `ca.key` | Local CA (sign server cert) |
| `server.crt` | Server certificate (SAN: `postgres`, `localhost`) |
| `server.key` | Server private key |

Production: replace with org CA or cloud provider certs; keep the same filenames or update compose mounts.

## 2. Enable SSL

`.env`:

```bash
POSTGRES_SSL=true
POSTGRES_USER=seo
POSTGRES_PASSWORD=seo_change_me
POSTGRES_DB=seo_autopilot

# App on host → Docker Postgres with SSL
DATABASE_URL=postgresql+asyncpg://seo:seo_change_me@localhost:5432/seo_autopilot?ssl=require

# Optional: verify CA (asyncpg / libpq style varies)
# DATABASE_URL=postgresql+asyncpg://seo:seo_change_me@localhost:5432/seo_autopilot?ssl=require
```

`POSTGRES_SSL` accepts: `true` / `on` / `1` → SSL **on**; anything else → **off**.

## 3. Start Postgres

```bash
docker compose --profile postgres up -d postgres
docker compose --profile postgres logs postgres | head -40
```

Confirm SSL:

```bash
docker compose --profile postgres exec postgres \
  psql -U seo -d seo_autopilot -c "SHOW ssl;"
# Expect: on
```

## 4. Application connection strings

| Client | Example |
|--------|---------|
| FastAPI (asyncpg) | `postgresql+asyncpg://USER:PASS@HOST:5432/DB?ssl=require` |
| Inside Compose (`backend-pg`) | host = `postgres`, add `?ssl=require` if SSL on |
| `psql` | `psql "host=localhost port=5432 dbname=seo_autopilot user=seo sslmode=require"` |
| pgAdmin SSL mode | **Require** (or Verify-CA + mount `ca.crt`) |

### Docker backend-pg with SSL

Set in `.env` before `up`:

```bash
POSTGRES_SSL=true
# backend-pg builds URL from user/pass; override fully if needed:
# DATABASE_URL=postgresql+asyncpg://seo:seo_change_me@postgres:5432/seo_autopilot?ssl=require
```

Update `backend-pg` environment to append `?ssl=require` when using SSL (see compose or set `DATABASE_URL` explicitly).

## 5. pgAdmin

1. Register server host `postgres`
2. **SSL** tab → Mode: **Require**
3. Optional Verify-CA: Root certificate = `certs/postgres/ca.crt` (copy into pgAdmin)

## 6. Strict production hardening

Edit `docker/postgres/pg_hba.conf` and **remove** non-SSL `host` lines so only `hostssl` remains:

```text
hostssl all all 0.0.0.0/0 scram-sha-256
hostssl all all ::/0      scram-sha-256
```

Then only TLS clients can connect.

## 7. Security notes

- Never commit `*.key` files (gitignored under `certs/`)
- `ssl_min_protocol_version = TLSv1.2`
- Internal Docker network already isolates traffic; SSL still protects host-published port `5432`
- Managed Postgres (RDS/Cloud SQL): use provider SSL; you usually do **not** run this cert script

## 8. Disable SSL

```bash
POSTGRES_SSL=off   # or unset
# DATABASE_URL without ?ssl=require
docker compose --profile postgres up -d --force-recreate postgres
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Permission denied on key | Entrypoint copies certs and `chmod 600` as `postgres` user |
| `SSL off` after enable | Set `POSTGRES_SSL=true` and recreate container |
| Client SSL error | Use `?ssl=require`; check host matches cert SAN (`localhost` / `postgres`) |
| Verify-full fails | Use `require` for self-signed, or trust `ca.crt` |
| Missing cert files | Run `bash scripts/generate-postgres-certs.sh` |

## Related

- [POSTGRES.md](./POSTGRES.md) – general Docker Postgres
- [PGADMIN.md](./PGADMIN.md) – pgAdmin UI TLS


## TLS 1.3 support

| Component | TLS 1.3 |
|-----------|---------|
| PostgreSQL 16 | Yes (via OpenSSL 3.x in official images) |
| `postgres:16-alpine` | Yes |
| Host OpenSSL 3.0+ | Yes |
| Current Compose default | `ssl_min_protocol_version=TLSv1.2` → **allows TLS 1.2 and 1.3** |

Minimum version is a floor: clients may negotiate **TLS 1.3** when both sides support it.

### Verify negotiated protocol (with SSL on)

```bash
# Inside network / from host with psql + openssl s_client
openssl s_client -connect localhost:5432 -starttls postgres -tls1_3 </dev/null 2>/dev/null | grep -E "Protocol|Cipher"

docker compose --profile postgres exec postgres   psql -U seo -d seo_autopilot -c "SHOW ssl_min_protocol_version;"
```

If `s_client` completes a handshake with `-tls1_3`, the server accepts TLS 1.3.

### Require TLS 1.3 only (optional, stricter)

In `docker-compose.yml` entrypoint, change:

```text
-c ssl_min_protocol_version=TLSv1.3
```

Or set via env later. Note: older clients that only speak TLS 1.2 will fail.

### asyncpg / app

`?ssl=require` enables TLS; the version is negotiated (typically 1.3 on modern stacks). There is no separate asyncpg URL flag for “TLS 1.3 only”.
