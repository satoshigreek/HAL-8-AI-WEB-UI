#!/usr/bin/env python3
"""Register the blockchain-tools sidecar routes as HAL 8 tool servers.

Idempotently upserts one OpenAPI tool-server connection per route of the
`blockchain-tools` mcpo sidecar (see deploy/blockchain-tools.json), granting
read access to all users — same pattern as the Apex Fusion registration.

Usage (from anywhere that can reach the HAL 8 API):
    HAL8_ADMIN_KEY=sk-... python3 scripts/register-blockchain-tool-servers.py \
        [--base-url https://hal8.odyssey-works.io]

Requires only the Python standard library.
"""

import argparse
import json
import os
import sys
import urllib.request

SERVERS = [
    {
        "id": "bnb-chain-read",
        "name": "BNB Chain (read-only)",
        "url": "http://blockchain-tools:8000/bnb",
        "description": (
            "Official BNB Chain data tools (read-only): BSC/opBNB blocks, "
            "transactions, balances, tokens, NFTs, contract reads, gas "
            "estimates, Greenfield storage queries. No transfers or "
            "signing — those tools are disabled server-side."
        ),
    },
    {
        "id": "ton-read",
        "name": "TON (read-only)",
        "url": "http://blockchain-tools:8000/ton",
        "description": (
            "Official TON tools (read-only, mainnet): Gram and jetton "
            "balances by address, transaction history, NFTs, TON DNS "
            "resolution, swap quotes, transaction emulation and unsigned "
            "transfer building. No signing, sending or wallet management — "
            "those tools are disabled server-side."
        ),
    },
    {
        "id": "near-read",
        "name": "NEAR (read-only)",
        "url": "http://blockchain-tools:8000/near",
        "description": (
            "Official NEAR tools (read-only): account summaries and "
            "balances, access-key listing, fungible-token search, contract "
            "inspection and read-only contract calls, Ref Finance pool "
            "data and swap estimates. No account changes, signing or "
            "transfers — those tools are disabled server-side."
        ),
    },
    {
        "id": "stellar-xdr",
        "name": "Stellar XDR codec",
        "url": "http://blockchain-tools:8000/stellar-xdr",
        "description": (
            "Official Stellar Development Foundation XDR tools: list XDR "
            "types, fetch JSON schemas, guess a value's type, and decode "
            "or encode Stellar XDR to/from JSON. Pure codec — no network, "
            "wallet or transaction capability."
        ),
    },
    {
        "id": "solana-docs",
        "name": "Solana developer docs",
        "url": "http://blockchain-tools:8000/solana-docs",
        "description": (
            "Official Solana Foundation developer MCP: semantic search and "
            "retrieval across current Solana ecosystem documentation, plus "
            "Anchor/Pinocchio program analysis. Documentation only — not a "
            "wallet."
        ),
    },
    {
        "id": "base-docs",
        "name": "Base documentation",
        "url": "http://blockchain-tools:8000/base-docs",
        "description": (
            "Official Base (Coinbase L2) documentation MCP: search and read "
            "docs.base.org content — Base Chain, Base Account, OnchainKit, "
            "agents. Documentation only — not a wallet."
        ),
    },
]


def api(base_url, key, method, path, body=None):
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://hal8.odyssey-works.io")
    args = ap.parse_args()

    key = os.environ.get("HAL8_ADMIN_KEY")
    if not key:
        sys.exit("Set HAL8_ADMIN_KEY (admin API key) in the environment.")

    current = api(args.base_url, key, "GET", "/api/v1/configs/tool_servers")
    connections = current.get("TOOL_SERVER_CONNECTIONS", [])
    by_url = {c.get("url"): i for i, c in enumerate(connections)}

    for server in SERVERS:
        connection = {
            "url": server["url"],
            "path": "openapi.json",
            "type": "openapi",
            "auth_type": "none",
            "key": "",
            "config": {"enable": True, "access_control": None},
            "info": {
                "id": server["id"],
                "name": server["name"],
                "description": server["description"],
            },
        }
        if server["url"] in by_url:
            connections[by_url[server["url"]]] = connection
            print(f"updated  {server['id']:<16} {server['url']}")
        else:
            connections.append(connection)
            print(f"added    {server['id']:<16} {server['url']}")

    api(args.base_url, key, "POST", "/api/v1/configs/tool_servers",
        {"TOOL_SERVER_CONNECTIONS": connections})
    print(f"\nSaved {len(SERVERS)} blockchain tool servers "
          f"({len(connections)} total connections).")
    print("Verify in Admin Panel → Settings → Tools, then test with a chat "
          "prompt like: 'What is the TON balance of <address>?'")


if __name__ == "__main__":
    sys.exit(main())
