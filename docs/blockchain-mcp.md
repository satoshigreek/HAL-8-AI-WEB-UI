# Blockchain MCP Integrations

First-party blockchain MCP servers wired into this repository's Claude Code
harness (`.mcp.json`, project scope). Only servers published or operated by a
chain's official foundation, protocol organization, core development company
or official GitHub organization are permitted. Community, generic multi-chain,
generic EVM, RPC-provider, wallet-company and exchange MCPs are prohibited —
see [blockchain-mcp-security.md](blockchain-mcp-security.md).

Registry of record: [`config/blockchain-mcp.registry.yaml`](../config/blockchain-mcp.registry.yaml)
Tool policy: [`config/blockchain-tool-policy.yaml`](../config/blockchain-tool-policy.yaml)

## Supported chains (6 of 13)

| Chain | Server ID | Source | Pin | Transport | Capability |
|---|---|---|---|---|---|
| Base | `base-mcp` | [mcp.base.org](https://mcp.base.org) (Base/Coinbase) | remote (manifest-hash tracked) | HTTP + Base Account OAuth | wallet, transfers, swaps, signing, contract calls, x402 — **writes blocked by harness policy** |
| Base (docs) | `base-docs` | [docs.base.org/mcp](https://docs.base.org/mcp) | remote (manifest-hash tracked) | HTTP, no auth | documentation search (read-only) |
| BNB Chain | `bnb-chain` | [`@bnb-chain/mcp`](https://github.com/bnb-chain/bnbchain-mcp) | `1.5.1` / commit `a133675` | stdio (npx) | reads, tx building/simulation; transfers & writes **blocked** |
| Solana | `solana` | [mcp.solana.com](https://github.com/solana-foundation/solana-mcp-official) | remote / reviewed commit `6be1bed` | HTTP, no auth | developer docs + program analysis only (**not** a wallet executor) |
| Stellar | `stellar-xdr` | [stellar/mcp-stellar-xdr](https://github.com/stellar/mcp-stellar-xdr) | commit `1e010ef4` via `deno@2.9.2` | stdio (npx deno) | XDR encode/decode only (**not** a wallet executor) |
| TON | `ton` | [`@ton/mcp`](https://github.com/ton-connect/kit) | `0.1.15-alpha.23` (alpha — exact pin) | stdio (npx) | reads, quotes, unsigned builds; wallet/signing tools **blocked** |
| NEAR | `near` | [`@nearai/near-mcp`](https://github.com/nearai/near-mcp) | `0.0.35` / commit `7d598bd` | stdio (npx) | public + contract reads; account/key/signing tools **blocked** |

Networks: BNB defaults to `bsc-testnet` (allowlist: BNB Smart Chain, opBNB,
Greenfield + testnets only — the server's other EVM networks are out of
policy). TON and NEAR default to `testnet`.

## Unsupported chains (7 of 13)

Bitcoin, Ethereum, XRP Ledger, TRON, Hyperliquid, Dogecoin and Zcash have **no
first-party MCP**. They are recorded in the registry with
`status: unsupported`, `reason: FIRST_PARTY_MCP_UNAVAILABLE`,
`community_substitution_allowed: false`. Requests for them must return:

```json
{
  "available": false,
  "reason": "FIRST_PARTY_MCP_UNAVAILABLE",
  "communitySubstitutionAllowed": false,
  "chain": "<CHAIN_ID>",
  "lastVerified": "<ISO_DATE>"
}
```

(`scripts/blockchain-mcp-healthcheck --chain <id>` prints exactly this.)
Never route these through a generic EVM/multi-chain/community server, a raw
RPC dressed up as an MCP, or another chain's server. XRPL note: xrpl.org lists
*third-party* MCP services; those are not first-party and stay disabled.

## Tool inventory & normalized namespaces

Native tool names (45 BNB, 40 TON, 23 NEAR, 5 Stellar, 5 Solana, 2 Base-docs)
are recorded per chain in the registry. Harness-facing normalized names
(`blockchain.<chain>.<capability>`) are mapped in
`config/blockchain-tool-policy.yaml` → `normalized_namespaces`; only tools
that exist in a discovered manifest get a mapping (Base wallet tools stay
unmapped until OAuth-gated discovery completes). Native names are preserved
for diagnostics and audit records.

## Site-facing bridge (HAL 8 models)

The read-only subset of these servers is also exposed to the deployed HAL 8
site's models via the `blockchain-tools` mcpo sidecar
(`docker-compose.prod.yaml` + `deploy/blockchain-tools.json`) and registered
as OpenAPI tool servers — see `DEPLOYMENT.md` → "Blockchain chain tools".
Write/signing/wallet tools are disabled at the bridge (no routes exist), and
the Base wallet MCP is not bridged (per-user OAuth). The harness setup below
is independent of the site bridge.

## Installation

The project-scoped config is committed as `.mcp.json` — cloning the repo and
starting Claude Code is enough; approve the project MCP servers when
prompted. Equivalent CLI form (already applied):

```bash
claude mcp add --scope project --transport http base-mcp https://mcp.base.org
claude mcp add --scope project --transport http base-docs https://docs.base.org/mcp
claude mcp add --scope project --transport http solana https://mcp.solana.com
# stdio servers are pinned in .mcp.json (npx -y <pkg>@<exact-version>)
```

Base requires completing the Base Account OAuth flow: run `/mcp` in Claude
Code, select `base-mcp`, and approve in Base Account. Never paste a private
key or seed phrase anywhere in this flow — Base Account OAuth is the only
supported authentication.

## Health checks

```bash
scripts/blockchain-mcp-healthcheck                 # all enabled servers
scripts/blockchain-mcp-healthcheck --only ton      # one server
scripts/blockchain-mcp-healthcheck --json out.json # machine-readable report
scripts/blockchain-mcp-healthcheck --update        # refresh registry hashes
scripts/blockchain-mcp-healthcheck --chain xrpl    # availability response
```

Per server it: initializes the MCP, lists tools, records the tool count,
hashes the manifest (sha256, canonical JSON), runs the registry-declared
harmless read-only operation, records latency, and flags **DRIFT** when the
live manifest hash differs from the registry baseline. It never signs,
broadcasts or changes state, and never triggers a write approval. An
unauthenticated `base-mcp` check passing means "OAuth requirement verified" —
wallet/balance queries run only after a user completes OAuth.

Note: sandboxed/CI environments with restricted egress may report the three
remote endpoints (`mcp.base.org`, `docs.base.org/mcp`, `mcp.solana.com`) as
`unreachable`; run the healthcheck from a normal network to verify them.

## Automated tests

```bash
python3 -m unittest discover -s tests/blockchain-mcp -v
```

Covers source integrity (first-party allowlist, exact pins, commit pins,
drift baselines), scope (exactly 13 registry entries, no substitutes, BNB
network allowlist, Solana/Stellar not wallet executors), security (mainnet
writes rejected, level-2 tools denied, confirmation-bypass blocked, unlimited
approvals rejected, secrets absent and redacted, prompt content cannot flip a
deny) and failure handling (unreachable endpoints, OAuth-missing, malformed
output, renamed/removed tools, manifest drift).

## Upgrade procedure

1. Read the upstream changelog/release notes for the new version or commit.
2. Bump the exact pin in `.mcp.json` **and** the matching
   `pinned_version`/`pinned_commit` in the registry (one reviewed commit).
3. Run `scripts/blockchain-mcp-healthcheck --only <server> --update` — review
   the manifest diff (added/removed tools) it reports.
4. Classify any new tools in `config/blockchain-tool-policy.yaml`
   (`tool_levels`) and mirror level ≥ 2 tools into the deny lists in
   `.claude/settings.json` and `FALLBACK_DENY` in `scripts/blockchain-mcp-audit`.
5. Run the test suite; it fails loudly if the layers drift apart.

## Troubleshooting

- **`npx` re-downloads every start** — expected; pins guarantee integrity,
  npx caches after first run.
- **`base-mcp` shows "needs authentication"** — run `/mcp`, complete the Base
  Account OAuth. Do not work around it with keys or tokens.
- **Healthcheck reports DRIFT** — the remote/updated server changed its tool
  manifest. Diff the reported added/removed tools, review upstream, then
  `--update` to accept the new baseline in a reviewed commit.
- **A write tool returns "Blocked by blockchain tool policy"** — intended.
  See the enablement procedure in
  [blockchain-mcp-security.md](blockchain-mcp-security.md); a prompt or env
  var alone can never enable it.
- **TON server can't find a wallet** — correct: no wallet is configured and
  wallet creation/import is disabled at this stage.
- **NEAR keystore** — the server uses a local unencrypted keystore under its
  HOME; never point it at `~/.near-credentials` / `~/.near-keystore`.
