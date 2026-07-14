"""Shared loaders for blockchain MCP tests.

Run the suite with:  python3 -m unittest discover -s tests/blockchain-mcp -v
"""

import json
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = REPO / "config" / "blockchain-mcp.registry.yaml"
POLICY_PATH = REPO / "config" / "blockchain-tool-policy.yaml"
MCP_JSON_PATH = REPO / ".mcp.json"
SETTINGS_PATH = REPO / ".claude" / "settings.json"
HEALTHCHECK_PATH = REPO / "scripts" / "blockchain-mcp-healthcheck"
AUDIT_PATH = REPO / "scripts" / "blockchain-mcp-audit"

APPROVED_CHAINS = [
    "bitcoin", "ethereum", "bnb-chain", "xrpl", "solana", "tron",
    "hyperliquid", "dogecoin", "zcash", "stellar", "base", "ton", "near",
]
ENABLED_CHAINS = {"bnb-chain", "solana", "stellar", "base", "ton", "near"}
UNSUPPORTED_CHAINS = set(APPROVED_CHAINS) - ENABLED_CHAINS

# First-party allowlist: the ONLY things .mcp.json may contain for
# blockchain servers.
APPROVED_NPM_PACKAGES = {
    "@bnb-chain/mcp",      # github.com/bnb-chain (BNB Chain org)
    "@ton/mcp",            # github.com/ton-connect/kit (TON official)
    "@nearai/near-mcp",    # github.com/nearai (NEAR AI)
    "deno",                # runtime only, used to execute the Stellar server
}
APPROVED_REMOTE_ENDPOINTS = {
    "https://mcp.base.org",
    "https://docs.base.org/mcp",
    "https://mcp.solana.com",
}
APPROVED_GIT_HOSTS = {"raw.githubusercontent.com/stellar/mcp-stellar-xdr"}
BLOCKCHAIN_SERVER_IDS = {
    "base-mcp", "base-docs", "bnb-chain", "solana", "stellar-xdr", "ton",
    "near",
}
# Known community / multi-chain / provider MCP packages that must never appear.
PROHIBITED_PACKAGE_MARKERS = [
    "evm-mcp", "mcp-evm", "web3-mcp", "multichain", "multi-chain",
    "alchemy", "infura", "quicknode", "moralis", "thirdweb", "metamask",
    "binance-mcp", "coinbase/agentkit", "goat-sdk", "crypto-mcp",
]


def load_registry():
    with open(REGISTRY_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_policy():
    with open(POLICY_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_mcp_json():
    with open(MCP_JSON_PATH, encoding="utf-8") as fh:
        return json.load(fh)["mcpServers"]


def load_settings():
    with open(SETTINGS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _import_script(path, name):
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(name, loader)
    mod = module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def import_healthcheck():
    return _import_script(HEALTHCHECK_PATH, "blockchain_mcp_healthcheck")


def import_audit():
    return _import_script(AUDIT_PATH, "blockchain_mcp_audit")
