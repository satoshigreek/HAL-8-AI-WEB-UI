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

## Apex Fusion chain tools

`docker-compose.prod.yaml` also runs two internal-only sidecars that give
every model access to the Apex Fusion tri-chain:

- **apex-mcp** — the official [Vector MCP server](https://github.com/Apex-Fusion/mcp-server)
  (18+ tools: balances, UTxOs, transactions, agent registry), built from
  source at deploy time and pointed at Vector **mainnet**. Wallet mnemonics
  are passed per-call by the model, never stored on the server; spend
  limits are configured conservatively (10 AP3X/tx, 50 AP3X/day).
- **apex-tools** — [mcpo](https://github.com/open-webui/mcpo), Open WebUI's
  MCP-to-OpenAPI adapter, exposing those tools at `http://apex-tools:8000`.

Register it once in **Admin Panel → Settings → Tools** as an OpenAPI tool
server with URL `http://apex-tools:8000` (no auth), available to all users.

## Blockchain chain tools (read-only)

A third internal-only sidecar, **blockchain-tools**, bridges the official
first-party MCP servers of six more ecosystems to HAL 8's models — the same
mcpo pattern as apex-tools, one route per chain:

| Route | Tools |
|---|---|
| `http://blockchain-tools:8000/bnb` | BNB Chain reads: blocks, txs, balances, tokens, NFTs, contract reads, Greenfield queries (26 tools) |
| `http://blockchain-tools:8000/ton` | TON mainnet reads: balances, history, jettons, NFTs, DNS, swap quotes, emulation (22 tools) |
| `http://blockchain-tools:8000/near` | NEAR reads: accounts, balances, token search, contract inspection/read calls (10 tools) |
| `http://blockchain-tools:8000/stellar-xdr` | Stellar XDR encode/decode (5 tools) |
| `http://blockchain-tools:8000/solana-docs` | Solana developer docs search + program analysis |
| `http://blockchain-tools:8000/base-docs` | Base (Coinbase L2) documentation search |

**Read-only by construction**: every transfer/signing/wallet/key tool is
listed in `disabledTools` in [`deploy/blockchain-tools.json`](deploy/blockchain-tools.json)
and gets no HTTP route at all (requests 404). No private keys, mnemonics or
wallets exist on the server. `tests/blockchain-mcp/test_site_bridge.py`
keeps the disabled list in sync with `config/blockchain-tool-policy.yaml`.
The Base *wallet* MCP (mcp.base.org) is intentionally not bridged — it
authenticates per-human via Base Account OAuth and must not be shared by a
multi-user site.

Register all six routes at once with the admin API:

```
HAL8_ADMIN_KEY=sk-... python3 scripts/register-blockchain-tool-servers.py
```

(or add each URL manually in **Admin Panel → Settings → Tools**, path
`openapi.json`, no auth). Package versions are exact-pinned; to upgrade, see
`docs/blockchain-mcp.md` → Upgrade procedure.

Note: the sidecar starts four Node.js MCP processes (~0.5 GB RSS combined).
On the 4 GB Lightsail instance keep an eye on `free -m` after deploying; if
memory gets tight, add a swapfile or upgrade the instance tier.

## Connecting models

HAL 8 serves the interface; it needs at least one model provider. In
**Admin Panel → Settings → Connections** add an OpenAI-compatible API
(HAL 8 inference endpoint, OpenRouter, vLLM, …) or an Ollama instance
reachable from the server.
