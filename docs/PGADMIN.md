# pgAdmin Docker setup – SEO Autopilot AI

Web UI for PostgreSQL. Compose profile: **`postgres`**.

## Quick start (HTTP)

```bash
docker compose --profile postgres up -d postgres pgadmin
```

Open: **http://localhost:5050**

| Field | Default |
|--------|---------|
| Email | `admin@example.com` (`PGADMIN_EMAIL`) |
| Password | `admin` (`PGADMIN_PASSWORD`) |

---

## Configure SSL / TLS (HTTPS for pgAdmin UI)

Official image supports TLS via `PGADMIN_ENABLE_TLS` and certs at:

- `/certs/server.cert`
- `/certs/server.key`

### 1. Generate certificates (dev / self-signed)

```bash
bash scripts/generate-pgadmin-certs.sh
# optional:
# CERT_CN=pgadmin.local bash scripts/generate-pgadmin-certs.sh
```

Files:

```text
certs/pgadmin/server.cert
certs/pgadmin/server.key
```

For production, replace with certificates from Let’s Encrypt or your CA (same filenames).

### 2. Enable TLS in `.env`

```bash
PGADMIN_ENABLE_TLS=True
PGADMIN_CONTAINER_PORT=443
PGADMIN_PORT=5050
# Optional login
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=strong_password_here
```

| Variable | HTTP (default) | HTTPS |
|----------|----------------|--------|
| `PGADMIN_ENABLE_TLS` | unset / empty | `True` |
| `PGADMIN_CONTAINER_PORT` | `80` | `443` |
| `PGADMIN_PORT` | host port, e.g. `5050` | host port, e.g. `5050` or `443` |

### 3. Restart pgAdmin

```bash
docker compose --profile postgres up -d pgadmin
```

Open: **https://localhost:5050**

Browser will warn on **self-signed** certs — accept for local dev, or install a trusted cert for production.

### 4. Compose mapping (reference)

```yaml
environment:
  PGADMIN_ENABLE_TLS: ${PGADMIN_ENABLE_TLS:-}
ports:
  - "${PGADMIN_PORT:-5050}:${PGADMIN_CONTAINER_PORT:-80}"
volumes:
  - ./certs/pgadmin/server.cert:/certs/server.cert:ro
  - ./certs/pgadmin/server.key:/certs/server.key:ro
```

When TLS is **disabled**, leave `PGADMIN_ENABLE_TLS` empty and `PGADMIN_CONTAINER_PORT=80`. Cert files can still be mounted (unused).

---

## Register Postgres server

**Object → Register → Server**

**General:** Name = `SEO Autopilot`

**Connection:**

| Field | Docker network value |
|-------|----------------------|
| Host | `postgres` |
| Port | `5432` |
| Database | `seo_autopilot` |
| Username | `seo` |
| Password | `POSTGRES_PASSWORD` |

### SSL mode (pgAdmin → Postgres)

Local Compose Postgres image does **not** require client SSL by default.

| SSL mode | When to use |
|----------|-------------|
| **Prefer** / **Allow** | Default local Docker |
| **Require** | Postgres has `ssl=on` and certs |
| **Verify-CA** / **Verify-Full** | Production managed Postgres (RDS, Cloud SQL) |

In pgAdmin: server → **Connection** / **SSL** tab → set mode, and if needed mount CA under **Root certificate**.

To enable SSL **on** the Postgres container itself, use a custom `postgresql.conf` + server certs (separate from pgAdmin UI TLS). For most local dev, HTTPS on **pgAdmin UI** is enough; DB stays on the internal Docker network.

---

## Production recommendations

1. Real certs (Let’s Encrypt) for `server.cert` / `server.key`
2. Strong `PGADMIN_PASSWORD`
3. Do not publish `5050`/`443` publicly without firewall / VPN
4. Prefer reverse proxy (Caddy/Traefik/Nginx) terminating TLS in front of pgAdmin HTTP, **or** native `PGADMIN_ENABLE_TLS`
5. Behind a reverse proxy, set correct proxy headers / `X-Script-Name` if served under a subpath

### Example: TLS at reverse proxy (pgAdmin stays HTTP internally)

```text
Internet → Caddy/Nginx (HTTPS) → pgadmin:80
PGADMIN_ENABLE_TLS unset
```

---

## Commands

```bash
# Certs
bash scripts/generate-pgadmin-certs.sh

# HTTP
docker compose --profile postgres up -d postgres pgadmin

# HTTPS (after .env TLS vars)
docker compose --profile postgres up -d pgadmin

docker compose --profile postgres logs -f pgadmin
docker compose --profile postgres down
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| HTTPS connection refused | `PGADMIN_ENABLE_TLS=True` and `PGADMIN_CONTAINER_PORT=443` |
| Missing cert errors in logs | Run `generate-pgadmin-certs.sh`; check mounts |
| Browser NET::ERR_CERT_AUTHORITY_INVALID | Expected for self-signed; use trusted cert in prod |
| Still on HTTP | Confirm env and recreate container: `up -d --force-recreate pgadmin` |
| Cannot connect to DB host `postgres` | Use service name, not `localhost`, from inside Compose |

## Related

- [POSTGRES.md](./POSTGRES.md)
