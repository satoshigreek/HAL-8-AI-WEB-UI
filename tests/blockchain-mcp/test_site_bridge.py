"""Site bridge: deploy/blockchain-tools.json stays read-only and in sync.

The blockchain-tools sidecar (docker-compose.prod.yaml) exposes blockchain
MCP tools to HAL 8 site models via mcpo. Every level >= 2 tool from the
policy must be in that server's disabledTools list (mcpo then creates no
route for it), pins must match the registry, and no wallet-capable OAuth
server may be bridged.
"""

import json
import unittest

from helpers import REPO, load_policy, load_registry

BRIDGE_PATH = REPO / "deploy" / "blockchain-tools.json"
COMPOSE_PATH = REPO / "docker-compose.prod.yaml"

# bridge server key -> policy server id
BRIDGE_TO_POLICY = {
    "bnb": "bnb-chain",
    "ton": "ton",
    "near": "near",
    "stellar-xdr": "stellar-xdr",
    "solana-docs": "solana",
    "base-docs": "base-docs",
}


class TestSiteBridge(unittest.TestCase):
    def setUp(self):
        with open(BRIDGE_PATH, encoding="utf-8") as fh:
            self.bridge = json.load(fh)["mcpServers"]
        self.policy = load_policy()
        self.registry = load_registry()

    def test_only_known_first_party_servers_bridged(self):
        self.assertEqual(set(self.bridge), set(BRIDGE_TO_POLICY))

    def test_base_wallet_mcp_not_bridged(self):
        blob = json.dumps(self.bridge)
        self.assertNotIn("mcp.base.org", blob,
                         "Base wallet MCP is per-user OAuth; never bridge it "
                         "to the shared site")

    def test_all_write_tools_disabled_on_bridge(self):
        for bridge_key, policy_id in BRIDGE_TO_POLICY.items():
            tool_levels = self.policy["servers"][policy_id].get("tool_levels") or {}
            required = {t for t, lvl in tool_levels.items() if lvl >= 2}
            disabled = set(self.bridge[bridge_key].get("disabledTools", []))
            self.assertEqual(
                disabled, required,
                f"{bridge_key}: disabledTools must exactly match the "
                f"level >= 2 tools in the policy")

    def test_bridge_pins_match_registry(self):
        chains = self.registry["chains"]
        self.assertIn(f"@bnb-chain/mcp@{chains['bnb-chain']['pinned_version']}",
                      self.bridge["bnb"]["args"])
        self.assertIn(f"@ton/mcp@{chains['ton']['pinned_version']}",
                      self.bridge["ton"]["args"])
        self.assertIn(f"@nearai/near-mcp@{chains['near']['pinned_version']}",
                      self.bridge["near"]["args"])
        stellar_url = [a for a in self.bridge["stellar-xdr"]["args"]
                       if a.startswith("https://")][0]
        self.assertIn(chains["stellar"]["pinned_commit"], stellar_url)

    def test_remote_bridge_urls_are_first_party(self):
        self.assertEqual(self.bridge["solana-docs"]["url"],
                         "https://mcp.solana.com")
        self.assertEqual(self.bridge["base-docs"]["url"],
                         "https://docs.base.org/mcp")
        for key in ("solana-docs", "base-docs"):
            self.assertEqual(self.bridge[key]["type"], "streamable-http")

    def test_no_keys_or_bypass_in_bridge_env(self):
        for key, cfg in self.bridge.items():
            env = cfg.get("env", {})
            for var in env:
                self.assertNotIn("PRIVATE_KEY", var, key)
                self.assertNotIn("MNEMONIC", var, key)
                self.assertNotIn("SEED", var, key)
        self.assertEqual(
            self.bridge["bnb"]["env"]["BNBCHAIN_MCP_SKIP_TRANSFER_CONFIRMATION"],
            "false")

    def test_compose_mounts_bridge_config(self):
        compose = COMPOSE_PATH.read_text(encoding="utf-8")
        self.assertIn("blockchain-tools:", compose)
        self.assertIn("./deploy/blockchain-tools.json", compose)
        self.assertIn("--config /app/blockchain-tools.json", compose)
        # internal-only: expose, never ports
        block = compose.split("blockchain-tools:")[1].split("caddy:")[0]
        self.assertIn("expose:", block)
        self.assertNotIn("ports:", block)


if __name__ == "__main__":
    unittest.main()
