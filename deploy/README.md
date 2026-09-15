# Deploying resoERP to a Linux VPS (aaPanel)

## What's in the box

- `docker-compose.yml` — three services:
  - `db` — PostgreSQL 15 (internal only, no public port)
  - `web` — Odoo 19 + reso_pms / reso_ownership (ports 8069/8072, keep private)
  - `website` — Angular booking site on port **8080** (this is the public entry point)
- `Dockerfile` / `website/Dockerfile` — multi-stage builds, nothing to install on the VPS beyond Docker.
- `deploy/nginx-resoerp.conf` — reverse-proxy config for aaPanel.
- `scripts/backup.sh` — nightly DB dump + filestore archive (14-day retention).

## One-time VPS setup

```bash
# 1. Install Docker + compose plugin (aaPanel also has a Docker app — either works)
curl -fsSL https://get.docker.com | sh

# 2. Get the code on the server
git clone <your-repo-url> resoERP   # or upload a zip and unzip
cd resoERP

# 3. Configure
cp .env.example .env
nano .env        # set DB_PASSWORD, ODOO_ADMIN_PASSWD, DEMO=false for production

# 4. Build and start
docker compose up -d --build

# 5. Watch the first boot (module install + demo data takes a few minutes)
docker compose logs -f web
```

## Pointing aaPanel/Nginx at it

1. In aaPanel add a site for `your-domain.com`, then in the site config use
   the server blocks from `deploy/nginx-resoerp.conf`
   (website → `127.0.0.1:8080`, backend subdomain → `127.0.0.1:8069`).
2. Enable SSL in aaPanel after HTTP works.
3. Close public access to ports 8069/8072 in the firewall — only 80/443 should be reachable.

## Operations

```bash
docker compose ps                 # status
docker compose logs -f web        # Odoo logs
docker compose up -d --build      # rebuild after code changes
docker compose exec web bash      # shell into Odoo container

# Upgrade module code on an existing database (does not touch data):
UPDATE_MODULES=reso_pms,reso_ownership docker compose up -d

# Backups (also ideal for a cron job):
./scripts/backup.sh
```

## Notes

- First boot installs `INIT_MODULES` with demo data when `DEMO=true` — perfect
  for trying everything out. The demo dataset now includes 200+ records:
  3 resorts, 6 room types, 11 rooms, 130+ bookings across the last 12 months
  and the next 30 days, folio outlet charges, owner registries and a
  distribution run — enough volume to explore the dashboard, analytics and
  occupancy reports realistically. For production, set `DEMO=false` **before**
  the first boot (the DB is created once; flipping it later has no effect on an
  existing database).
- Odoo runs with `proxy_mode = True` and 2 workers — `/websocket` and
  `/longpolling` must be proxied to port 8072 as shown in the nginx config.
