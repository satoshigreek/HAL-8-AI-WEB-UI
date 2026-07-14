"""Scope: exactly 13 chains, no substitutes, correct capability posture."""

import unittest

from helpers import (
    APPROVED_CHAINS, ENABLED_CHAINS, UNSUPPORTED_CHAINS,
    load_mcp_json, load_policy, load_registry,
)

BNB_ALLOWED_NETWORKS = {"bsc", "bsc-testnet", "opbnb", "opbnb-testnet",
                        "greenfield", "greenfield-testnet"}
NON_BNB_EVM_NETWORKS = {"ethereum", "eth", "mainnet", "base", "base-sepolia",
                        "arbitrum", "arb", "optimism", "matic", "polygon",
                        "iotex", "avalanche", "fantom"}


class TestScope(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry()
        self.policy = load_policy()
        self.chains = self.registry["chains"]

    def test_exactly_thirteen_registry_entries(self):
        self.assertEqual(len(self.chains), 13)
        self.assertEqual(set(self.chains), set(APPROVED_CHAINS))
        self.assertEqual(list(self.registry["approved_scope"]), APPROVED_CHAINS)

    def test_only_approved_first_party_chains_enabled(self):
        enabled = {cid for cid, e in self.chains.items()
                   if e.get("enabled") or e.get("status") == "enabled"}
        self.assertEqual(enabled, ENABLED_CHAINS)

    def test_unsupported_chains_cannot_load_substitutes(self):
        for cid in UNSUPPORTED_CHAINS:
            e = self.chains[cid]
            self.assertEqual(e["status"], "unsupported", cid)
            self.assertEqual(e["reason"], "FIRST_PARTY_MCP_UNAVAILABLE", cid)
            self.assertFalse(e["community_substitution_allowed"], cid)
            self.assertFalse(e["enabled"], cid)
            self.assertIsNone(e["package"], cid)
            self.assertIsNone(e["endpoint"], cid)
            self.assertIsNone(e["mcp_server_id"], cid)

    def test_unsupported_chain_response_shape(self):
        from helpers import import_healthcheck
        hc = import_healthcheck()
        for cid in sorted(UNSUPPORTED_CHAINS):
            resp = hc.unsupported_chain_response(cid, "2026-07-14")
            self.assertEqual(resp, {
                "available": False,
                "reason": "FIRST_PARTY_MCP_UNAVAILABLE",
                "communitySubstitutionAllowed": False,
                "chain": cid,
                "lastVerified": "2026-07-14",
            })

    def test_no_unsupported_chain_has_mcp_json_entry(self):
        servers = load_mcp_json()
        for cid in UNSUPPORTED_CHAINS:
            self.assertNotIn(cid, servers)
        # and nothing generic that could route them
        for sid in servers:
            self.assertNotIn("evm", sid.lower())
            self.assertNotIn("multi", sid.lower())

    def test_bnb_cannot_route_to_unrelated_evm_networks(self):
        allowlist = set(self.policy["servers"]["bnb-chain"]["network_allowlist"])
        self.assertEqual(allowlist, BNB_ALLOWED_NETWORKS)
        self.assertFalse(allowlist & NON_BNB_EVM_NETWORKS)
        reg_networks = set(self.chains["bnb-chain"]["supported_networks"])
        self.assertEqual(reg_networks, BNB_ALLOWED_NETWORKS)
        self.assertEqual(self.chains["bnb-chain"]["default_network"],
                         "bsc-testnet")

    def test_stellar_is_not_a_wallet_executor(self):
        e = self.chains["stellar"]
        self.assertTrue(e["read_only"])
        self.assertFalse(e["wallet_capable"])
        self.assertFalse(e["transaction_capable"])
        self.assertEqual(set(e["capability_classes"]), {"xdr_codec"})
        pol = self.policy["servers"]["stellar-xdr"]
        self.assertFalse(pol["signing_enabled"])
        self.assertFalse(pol["submission_enabled"])
        self.assertFalse(pol["wallet_access"])

    def test_solana_is_not_a_wallet_executor(self):
        e = self.chains["solana"]
        self.assertTrue(e["read_only"])
        self.assertFalse(e["wallet_capable"])
        self.assertFalse(e["transaction_capable"])
        self.assertEqual(set(e["capability_classes"]),
                         {"docs", "program_analysis"})
        pol = self.policy["servers"]["solana"]
        self.assertEqual(pol["capability"], "developer_tooling")
        self.assertFalse(pol["wallet_access"])
        self.assertFalse(pol["signing_enabled"])
        self.assertFalse(pol["broadcasting_enabled"])

    def test_xrpl_third_party_integrations_remain_disabled(self):
        e = self.chains["xrpl"]
        self.assertEqual(e["status"], "unsupported")
        self.assertFalse(e["community_substitution_allowed"])
        self.assertIn("third", (e["notes"] or "").lower())

    def test_normalized_names_only_for_discovered_tools(self):
        ns = self.policy["normalized_namespaces"]
        for sid, mapping in ns.items():
            chain = self.policy["servers"][sid]["chain"]
            entry = self.chains[chain]
            if sid == "base-docs":
                inventory = set(entry["docs_server"]["tool_inventory"]["tools"])
            else:
                inventory = set((entry.get("tool_inventory") or {}).get("tools", []))
            for norm, native in mapping.items():
                self.assertTrue(norm.startswith("blockchain."), norm)
                if native is not None:
                    self.assertIn(native, inventory,
                                  f"{norm} maps to undiscovered tool {native}")
        # base-mcp wallet tools are undiscovered pre-OAuth: all null
        self.assertTrue(all(v is None for v in ns["base-mcp"].values()))

    def test_tool_groups_isolation(self):
        groups = self.policy["tool_groups"]
        for name in ("blockchain-read", "blockchain-docs", "blockchain-base",
                     "blockchain-bnb", "blockchain-solana",
                     "blockchain-stellar", "blockchain-ton",
                     "blockchain-near", "blockchain-security-review"):
            self.assertIn(name, groups)
        for name in ("blockchain-read", "blockchain-docs",
                     "blockchain-security-review"):
            self.assertEqual(groups[name]["max_level"], 0,
                             f"{name} must not include signing/write tools")
        self.assertFalse(
            self.policy["isolation_rules"]["read_only_agents_get_signing_tools"])


if __name__ == "__main__":
    unittest.main()
