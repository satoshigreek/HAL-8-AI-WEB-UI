"""Source integrity: only pinned, first-party MCP servers are configured."""

import re
import unittest

from helpers import (
    APPROVED_NPM_PACKAGES, APPROVED_REMOTE_ENDPOINTS, BLOCKCHAIN_SERVER_IDS,
    PROHIBITED_PACKAGE_MARKERS, load_mcp_json, load_registry,
)

EXACT_VERSION_RE = re.compile(r"^@?[\w./-]+@\d+\.\d+\.\d+(-[\w.]+)?$")
COMMIT_SHA_RE = re.compile(r"/([0-9a-f]{40})/")


class TestSourceIntegrity(unittest.TestCase):
    def setUp(self):
        self.servers = load_mcp_json()
        self.registry = load_registry()

    def blockchain_servers(self):
        return {k: v for k, v in self.servers.items()
                if k in BLOCKCHAIN_SERVER_IDS}

    def test_every_enabled_server_is_on_first_party_allowlist(self):
        for sid, cfg in self.blockchain_servers().items():
            if "url" in cfg:
                self.assertIn(cfg["url"], APPROVED_REMOTE_ENDPOINTS,
                              f"{sid}: remote endpoint not on allowlist")
            else:
                pkg_args = [a for a in cfg.get("args", [])
                            if not a.startswith("-") and "@" in a]
                self.assertTrue(pkg_args, f"{sid}: no package in args")
                for arg in pkg_args:
                    base = arg.rsplit("@", 1)[0]
                    self.assertIn(base, APPROVED_NPM_PACKAGES,
                                  f"{sid}: package {base} not first-party")

    def test_no_community_or_multichain_packages(self):
        blob = str(self.servers).lower()
        for marker in PROHIBITED_PACKAGE_MARKERS:
            self.assertNotIn(marker, blob,
                             f"prohibited package marker found: {marker}")

    def test_local_packages_use_exact_pinned_versions(self):
        for sid, cfg in self.blockchain_servers().items():
            for arg in cfg.get("args", []):
                if arg.startswith("-") or "@" not in arg or arg.startswith("http"):
                    continue
                self.assertNotIn("@latest", arg, f"{sid}: floating @latest")
                self.assertNotRegex(arg, r"@alpha$", f"{sid}: floating @alpha")
                self.assertRegex(arg, EXACT_VERSION_RE,
                                 f"{sid}: {arg} is not an exact semver pin")

    def test_git_based_integration_is_commit_pinned(self):
        stellar = self.servers["stellar-xdr"]
        url = [a for a in stellar["args"] if a.startswith("https://")][0]
        self.assertIn("raw.githubusercontent.com/stellar/mcp-stellar-xdr", url)
        m = COMMIT_SHA_RE.search(url)
        self.assertIsNotNone(m, "stellar URL must embed a 40-hex commit SHA")
        self.assertNotIn("/main/", url, "must not execute unpinned main branch")
        self.assertNotIn("/master/", url)
        reg_commit = self.registry["chains"]["stellar"]["pinned_commit"]
        self.assertEqual(m.group(1), reg_commit,
                         "registry pinned_commit must match .mcp.json URL")

    def test_registry_pins_match_mcp_json(self):
        chains = self.registry["chains"]
        bnb = chains["bnb-chain"]
        self.assertIn(f"{bnb['package']}@{bnb['pinned_version']}",
                      self.servers["bnb-chain"]["args"])
        ton = chains["ton"]
        self.assertIn(f"{ton['package']}@{ton['pinned_version']}",
                      self.servers["ton"]["args"])
        near = chains["near"]
        self.assertIn(f"{near['package']}@{near['pinned_version']}",
                      self.servers["near"]["args"])

    def test_remote_manifest_change_detection_is_configured(self):
        # Drift detection requires a recorded manifest_hash for every server
        # verified so far; the healthcheck compares live hashes against these.
        for chain_id in ("bnb-chain", "stellar", "ton", "near"):
            entry = self.registry["chains"][chain_id]
            self.assertRegex(entry["manifest_hash"] or "", r"^[0-9a-f]{64}$",
                             f"{chain_id}: missing manifest hash baseline")

    def test_remote_servers_record_endpoint_and_auth(self):
        for chain_id in ("solana", "base"):
            entry = self.registry["chains"][chain_id]
            self.assertTrue(entry["endpoint"].startswith("https://"))
            self.assertIn("auth_method", entry["health_check"])
            self.assertTrue(entry["last_verified"])


if __name__ == "__main__":
    unittest.main()
