# Blockchain MCP Security Model

Security posture for the first-party blockchain MCP integrations described in
[blockchain-mcp.md](blockchain-mcp.md). The enforced artifacts are
`config/blockchain-tool-policy.yaml`, `.claude/settings.json`
(permission allow/deny lists + hooks) and `scripts/blockchain-mcp-audit`
(PreToolUse deny backstop + audit log). `tests/blockchain-mcp/` keeps the
three layers consistent.

## Threat model

| Threat | Mitigation |
|---|---|
| Malicious/compromised MCP package (supply chain) | First-party allowlist only; exact version pins; git integrations pinned to a reviewed commit; no floating `@latest`/`@alpha`; manifest hash drift detection |
| Remote server silently changes behavior | Manifest sha256 baseline in registry; healthcheck flags DRIFT and lists added/removed tools |
| Prompt injection via MCP output (docs, tool results, error text) | All MCP output is untrusted input (`mcp_output_is_untrusted: true`); permission decisions live in committed config + hook code, which prompt content cannot alter (tested) |
| Unintended transfers/signing | Every level ≥ 2 tool (signing, broadcast, transfer, swap, approval, wallet/account/key management, x402) is deny-listed AND hook-blocked at install; BNB confirmation bypass pinned off, per-call `skipConfirmation` rejected |
| Mainnet fund loss | Level 3 (mainnet state change) is hard-disabled; enabling requires code + policy change, security review, separate signer, chain tests, explicit enablement, per-tx human approval — never a prompt or env var |
| Key/seed exposure | No keys configured anywhere; secret-shaped values and sensitive keys redacted from audit logs; secret patterns tested absent from committed files; `get_address_from_private_key` and `account_export_account` denied |
| Wrong-network execution | BNB network allowlist (BNB ecosystems only); TON/NEAR default `testnet`; unsupported chains return structured refusals instead of routing to substitutes |
| Unlimited token approvals | Rejected by policy and by the pre-hook (`amount: max/unlimited/infinite`) |

## First-party allowlist policy

Enabled: Base (`mcp.base.org` + `docs.base.org/mcp`), BNB Chain
(`@bnb-chain/mcp`), Solana Foundation (`mcp.solana.com`), Stellar SDF
(`stellar/mcp-stellar-xdr`), TON (`@ton/mcp`), NEAR AI (`@nearai/near-mcp`).
Everything else — community, multi-chain, generic EVM, RPC-provider,
wallet-company, exchange, unofficial wrappers, archived projects — is
prohibited, including as a fallback when a first-party server fails.
Bitcoin, Ethereum, XRPL, TRON, Hyperliquid, Dogecoin, Zcash: unsupported, no
substitution (`community_substitution_allowed: false`).

## Tool permission levels

- **Level 0 — automatic read**: docs search, public network/block/tx/account
  queries, balances, token metadata, contract reads, XDR codec, fee
  estimates, non-signing swap quotes, simulation, program analysis. Allowed
  in `.claude/settings.json`.
- **Level 1 — unsigned construction**: TON `build_*` only. No key loaded,
  nothing signed/broadcast, network displayed, payload labeled unsigned.
- **Level 2 — approved testnet action**: every signature, broadcast,
  transfer, swap, approval, contract write/deploy, stake, wallet
  create/import, account create/delete, access-key change, NFT transfer,
  x402 payment. Requires explicit per-invocation human approval showing
  chain, network, wallet, action, destination, asset, amount, fee, contract,
  decoded method, approval amount, slippage, simulation result and expected
  balance changes. **Currently denied outright** (`initially_denied: true`).
- **Level 3 — mainnet state change**: hard-disabled. Enablement requires all
  of: source-code change, policy change, security review, separate signer
  configuration, chain-specific tests, explicit chain enablement, and human
  approval per transaction.

Server-specific posture:

- **Base** — OAuth wallet-capable and transaction-capable. Base Account has
  its own approval UI, but the harness independently blocks write tools
  (`default_unknown_tool_level: 2` until the OAuth-gated manifest is
  discovered and classified). Confirmation links are never auto-opened or
  auto-approved.
- **BNB Chain** — transaction-capable. `BNBCHAIN_MCP_SKIP_TRANSFER_CONFIRMATION`
  pinned `"false"`; no `PRIVATE_KEY` configured; non-BNB EVM networks out of
  policy.
- **Solana** — developer/documentation-focused. Not a wallet executor.
- **Stellar** — XDR-focused. Not a wallet or submission server. Deno runs the
  pinned script with `--allow-read` only.
- **TON** — **alpha, wallet-capable, internally signing**: the server itself
  holds keys and signs. Treated as the most privileged server; every wallet
  management, signing and broadcast tool is denied at install; `NETWORK`
  pinned `testnet`; no `MNEMONIC`/`PRIVATE_KEY` set.
- **NEAR** — wallet, account-management and transaction-capable, with a
  local **unencrypted** keystore. All account/key/signing/sending tools
  denied at install.

## OAuth handling (Base)

Base Account OAuth is the only authentication used. The user completes it
interactively (`/mcp` → `base-mcp` → approve in Base Account). Tokens are
managed by the Claude Code MCP client; they are never committed, logged
(redaction covers tokens) or exported. No private key or seed phrase is ever
requested, stored or imported for Base.

## Wallet isolation

MCP servers must never be given access to treasury, foundation, corporate,
exchange, market-making, liquidity-management or personal custody wallets, or
production NEAR keystores (`~/.near-credentials`, `~/.near-keystore` are
prohibited paths and gitignored). Any future wallet for testnet work must be
a dedicated, freshly created, minimally funded agent wallet.

## Secret management

Never committed (tested): private keys, seed phrases, mnemonics, keystores,
wallet backups, OAuth tokens, API credentials, session tokens, Base Account
artifacts. `.env.example` documents variable *names* only. No dummy keys or
test mnemonics are created. Audit logs redact sensitive keys and
secret-shaped strings before write.

## Mainnet activation procedure

1. Open a PR changing `config/blockchain-tool-policy.yaml` (chain-scoped) and
   the code paths involved — a reviewed source change, not a toggle.
2. Complete a security review of the diff (document in the PR).
3. Configure a separate signer (dedicated wallet, never a custody/production
   wallet) outside the repository.
4. Add and pass chain-specific tests for the exact write paths enabled.
5. Explicitly enable only the target chain; all others stay disabled.
6. Every transaction still requires human approval with the full level-2
   display fields. No blanket approvals.

## Approval process (testnet writes, once enabled)

Write tools move from `deny` to prompt-based approval per invocation. The
pre-hook logs `approval_required: true`; execution implies the user approved
via the permission prompt (`approval_received: true` in the post record).
The approval prompt must present the full field list from
`permission_levels[2].approval_display_fields`.

## Audit log

Location: `.claude/blockchain-audit/audit-YYYY-MM-DD.jsonl` (gitignored).
Every blockchain MCP invocation is recorded pre- and post-execution with:
timestamp, request id, agent/session id, server id, native + normalized tool
name, chain, network, risk level, wallet address, redacted parameters,
approval flags, simulation result, transaction hash, redacted result, error
and duration. Redacted before write: private keys, mnemonics, seed phrases,
auth/OAuth tokens, keystore contents, sensitive env values.

## Incident response

1. **Suspected key/token compromise** — revoke first: Base Account →
   dashboard → revoke the connector authorization; TON → owner dashboard →
   revoke operator key / withdraw; NEAR → rotate/delete the affected access
   keys from a trusted machine; BNB → move funds from the affected key.
2. Disable the server: set `enabled: false` in the registry and remove the
   entry from `.mcp.json` (commit immediately; both are read at session
   start).
3. Preserve `.claude/blockchain-audit/` logs for the affected window.
4. Diff the manifest (healthcheck) and pin state against the last reviewed
   baseline to rule out supply-chain drift.
5. Re-enable only after a reviewed PR restores a verified pin and the test
   suite passes.

## Server-specific risks

- **TON (alpha)**: internal key handling means a server bug = key exposure;
  obfuscated (not encrypted) on-disk wallet registry; API may change between
  alpha releases — never upgrade without reviewing the changelog.
- **NEAR**: unencrypted local keystore; `account_export_account` exports
  secrets (denied); account deletion is irreversible (denied).
- **BNB**: accepts `privateKey` as a *tool parameter* on some tools — a
  conversation-history exposure hazard; those tools are denied and the
  pattern is redacted from logs.
- **Base**: remote manifest can change server-side at any time (drift
  detection); OAuth phishing — only ever authorize at the genuine Base
  Account origin, never via a link produced by model output.
- **Solana / Stellar / Base-docs**: read-only; primary residual risk is
  prompt injection through returned content — covered by the untrusted-input
  rule.
