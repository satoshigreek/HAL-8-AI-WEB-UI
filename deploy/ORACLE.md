# HAL 8 on Oracle Cloud Always Free — click-by-click

Oracle's Always Free tier gives you a permanently free ARM server (up to
4 cores / 24 GB RAM) that comfortably runs HAL 8. Total setup: ~15 minutes.
No terminal needed — the included cloud-init script configures the server
itself on first boot.

## 1. Create the Oracle account (~5 min)

1. Go to https://www.oracle.com/cloud/free/ and click **Start for free**.
2. Sign up with your email and company details. A credit/debit card is
   required for identity verification — **Always Free resources never charge
   it**. Pick a home region close to you (e.g. UAE East - Dubai, or
   Frankfurt); note that Always Free capacity varies by region.
3. Wait for the "your account is ready" email and sign in to the console.

## 2. Create the server (~5 min)

1. Console menu ☰ → **Compute → Instances → Create instance**.
2. Name: `hal8`.
3. **Image and shape** → Edit:
   - Image: **Ubuntu** → *Canonical Ubuntu 24.04*.
   - Shape: **Ampere → VM.Standard.A1.Flex**, set **4 OCPUs / 24 GB**
     (that's the full free allowance; 2/12 also works).
     If A1 shows "out of capacity", try again later, another availability
     domain, or fall back to the free AMD micro shape (slower).
4. **Add SSH keys**: choose "Generate a key pair for me" and download the
   private key (you likely won't need it, but keep it — it's the only way
   to log in later).
5. Expand **Advanced options** (bottom) → **Management → Cloud-init**:
   paste the entire contents of
   [`deploy/oracle-cloud-init.yaml`](./oracle-cloud-init.yaml).
   - Using a hostname other than `chat.hal8.ai`? Edit the `HAL8_DOMAIN`
     line in what you paste.
6. Click **Create**. When the instance is Running, copy its **Public IP**.

## 3. Open ports 80/443 in Oracle's network firewall (~2 min)

Oracle blocks web traffic at the network level by default — this step is
mandatory and the most commonly missed one:

1. On the instance page, click its **subnet** link, then the
   **Default Security List**.
2. **Add Ingress Rules** — add these two:
   - Source CIDR `0.0.0.0/0`, protocol **TCP**, destination port **80**
   - Source CIDR `0.0.0.0/0`, protocol **TCP**, destination port **443**

(The host's own firewall is opened automatically by the cloud-init script.)

## 4. Point DNS (~2 min)

At your DNS provider for `hal8.ai`, add an **A record**:

```
chat.hal8.ai  →  <the instance's Public IP>
```

## 5. Wait for the first build, then log in

The server builds the app from source on first boot — allow **15–25
minutes** after instance creation. Then open **https://chat.hal8.ai**:

- The first account created becomes the **admin** — create yours
  immediately.
- Add a model provider under **Admin Panel → Settings → Connections**
  (any OpenAI-compatible API or an Ollama instance).
- Keep signups admin-approved (the default) to stay within the upstream
  license's 50-user branding condition — see `DEPLOYMENT.md` §4.

## Troubleshooting

- **Site unreachable after 30 min** — 90% of the time it's step 3
  (security list ingress rules). Check those first, then that DNS resolves
  to the right IP (`https://dnschecker.org`).
- **Certificate errors in the first minutes** — Caddy retries TLS issuance
  automatically once DNS propagates; give it a few minutes.
- **Inspect the first launch** — SSH in with the downloaded key
  (`ssh -i <key> ubuntu@<ip>`) and check `/var/log/hal8-first-launch.log`
  or `sudo docker ps`.
- **Oracle idle reclamation** — Oracle may reclaim *idle* Always Free
  instances. Real usage prevents this; upgrading the account to
  pay-as-you-go (still $0 within free limits) removes the policy entirely.

## Updating later

SSH in and run:

```bash
cd /opt/hal8 && sudo git pull && sudo docker compose -f docker-compose.prod.yaml up -d --build
```
