# Deploying HAL 8 to a public website

This guide takes the HAL 8 web UI live on your own server at a public URL
(e.g. `https://chat.hal8.ai`) with automatic HTTPS.

> **Deploying on Oracle Cloud's Always Free tier?** Follow the click-by-click
> guide in [deploy/ORACLE.md](./deploy/ORACLE.md) — it uses a cloud-init script
> so the server configures itself with no terminal commands.

## What you need

- A Linux server (VPS or dedicated) with **Docker + the compose plugin** installed,
  ports **80 and 443** open, and at least **2 GB RAM**
  (4 GB if you build the image on the server instead of pulling it).
- A DNS record you control on `hal8.ai` (or any domain).

## 1. Point DNS at the server

At your DNS provider for `hal8.ai`, create an **A record**:

```
chat.hal8.ai  →  <your server's public IPv4>
```

(Any subdomain works — set `HAL8_DOMAIN` accordingly below.)

## 2. Get the code and configure

```bash
git clone https://github.com/satoshigreek/HAL-8-AI-WEB-UI.git
cd HAL-8-AI-WEB-UI

cat > .env <<EOF
WEBUI_SECRET_KEY=$(openssl rand -hex 32)
HAL8_DOMAIN=chat.hal8.ai
EOF
```

## 3. Launch

```bash
docker compose -f docker-compose.prod.yaml up -d --build
```

- The first build takes several minutes (frontend + backend image).
  Once this repository's `main` branch has published an image via the bundled
  GitHub Actions workflow, you can skip building and pull instead:
  `docker compose -f docker-compose.prod.yaml pull hal8 && docker compose -f docker-compose.prod.yaml up -d`
- Caddy obtains and renews the TLS certificate automatically as soon as the
  DNS record resolves to the server.

Open `https://chat.hal8.ai` — the **first account created becomes the admin**.
Do this yourself right after launch.

## 4. Keep the deployment license-compliant

This rebranded interface relies on the Open WebUI license condition allowing
branding changes for deployments with **≤ 50 users in any rolling 30-day
period** (see `LICENSE` and `README.md`):

- New signups default to the **pending** role and only get access after an
  admin approves them (Admin Panel → Users), so user count stays under your
  control.
- Once your team is onboarded you can close signups entirely:
  set `ENABLE_SIGNUP=false` in `.env` and re-run the `up -d` command.

## 5. Operate

```bash
# update to the latest code
git pull && docker compose -f docker-compose.prod.yaml up -d --build

# logs
docker compose -f docker-compose.prod.yaml logs -f hal8

# back up all app data (users, chats, settings)
docker run --rm -v hal-8-ai-web-ui_hal8-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/hal8-data-backup.tgz -C /data .
```

All persistent state lives in the `hal8-data` Docker volume (SQLite + uploads).

Styling overrides (including the mobile app-feel layer) live in
`deploy/custom.css`, bind-mounted into the container — edit it, `git pull`
on the server, and re-run the `up -d` command; no image rebuild needed.

## Connecting models

HAL 8 serves the interface; it needs at least one model provider. In
**Admin Panel → Settings → Connections** add an OpenAI-compatible API
(HAL 8 inference endpoint, OpenRouter, vLLM, …) or an Ollama instance
reachable from the server.
