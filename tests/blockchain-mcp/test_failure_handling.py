"""Failure handling: the healthcheck degrades gracefully, never crashes."""

import json
import unittest

from helpers import import_healthcheck, load_mcp_json, load_policy

hc = import_healthcheck()


class TestManifestHandling(unittest.TestCase):
    TOOLS = [
        {"name": "b_tool", "description": "b", "inputSchema": {"type": "object"}},
        {"name": "a_tool", "description": "a", "inputSchema": {"type": "object"}},
    ]

    def test_hash_is_order_independent(self):
        h1 = hc.canonical_manifest_hash(self.TOOLS)
        h2 = hc.canonical_manifest_hash(list(reversed(self.TOOLS)))
        self.assertEqual(h1, h2)
        self.assertRegex(h1, r"^[0-9a-f]{64}$")

    def test_manifest_change_detected(self):
        h1 = hc.canonical_manifest_hash(self.TOOLS)
        changed = [dict(self.TOOLS[0], description="CHANGED"), self.TOOLS[1]]
        self.assertNotEqual(h1, hc.canonical_manifest_hash(changed))

    def test_tool_renamed_upstream(self):
        added, removed = hc.diff_inventory(
            ["a_tool", "b_tool"], ["a_tool", "b_tool_v2"])
        self.assertEqual(added, ["b_tool_v2"])
        self.assertEqual(removed, ["b_tool"])

    def test_tool_removed_upstream(self):
        added, removed = hc.diff_inventory(["a_tool", "b_tool"], ["a_tool"])
        self.assertEqual(added, [])
        self.assertEqual(removed, ["b_tool"])


class TestErrorClassification(unittest.TestCase):
    def test_oauth_not_completed(self):
        self.assertEqual(hc.classify_http_error(401), "auth_required")
        self.assertEqual(hc.classify_http_error(403), "auth_required")

    def test_endpoint_errors(self):
        self.assertEqual(hc.classify_http_error(404), "error")
        self.assertEqual(hc.classify_http_error(503), "unreachable")

    def test_malformed_mcp_output(self):
        with self.assertRaises(Exception):
            hc.parse_sse_or_json("this is not json", "application/json")
        with self.assertRaises(Exception):
            hc.parse_sse_or_json("event: message\n\n", "text/event-stream")

    def test_sse_and_json_parsing(self):
        msg = {"jsonrpc": "2.0", "id": 1, "result": {}}
        self.assertEqual(hc.parse_sse_or_json(json.dumps(msg),
                                              "application/json"), msg)
        sse = f"event: message\ndata: {json.dumps(msg)}\n\n"
        self.assertEqual(hc.parse_sse_or_json(sse, "text/event-stream"), msg)


class TestUnavailableEndpoint(unittest.TestCase):
    def test_unreachable_endpoint_reported_not_raised(self):
        entry = {
            "transport": "http",
            "endpoint": "https://127.0.0.1:1",  # nothing listens here
            "health_check": {"method": "http", "auth_method": "none"},
        }
        result = hc.check_server("dead", "testchain", entry, {}, timeout=3)
        self.assertIn(result["status"], ("unreachable", "error"))
        self.assertIsNotNone(result["error"])

    def test_mcp_initialization_failure_stdio(self):
        entry = {"transport": "stdio", "health_check": {"method": "stdio"}}
        servers = {"broken": {"command": "false", "args": []}}
        result = hc.check_server("broken", "testchain", entry, servers, timeout=3)
        self.assertIn(result["status"], ("unreachable", "error"))

    def test_missing_stdio_config(self):
        entry = {"transport": "stdio", "health_check": {"method": "stdio"}}
        result = hc.check_server("ghost", "testchain", entry, {}, timeout=3)
        self.assertIn(result["status"], ("unreachable", "error"))


class TestNetworkValidation(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()

    def test_invalid_chain_id_returns_structured_error(self):
        registry_chains = {"bnb-chain", "solana"}
        self.assertNotIn("fakechain", registry_chains)
        resp = hc.unsupported_chain_response("fakechain", "2026-07-14")
        self.assertFalse(resp["available"])

    def test_unsupported_network_rejected_by_allowlist(self):
        allowlist = self.policy["servers"]["bnb-chain"]["network_allowlist"]
        for bad in ("ethereum", "base", "arbitrum", "polygon"):
            self.assertNotIn(bad, allowlist)

    def test_harmless_calls_are_read_only(self):
        # No registry harmless op may be a signing/sending/wallet tool.
        from helpers import load_registry
        registry = load_registry()
        forbidden = ("send", "transfer", "sign", "create", "delete",
                     "import", "approve", "swap_execute", "deploy")
        for cid, entry in registry["chains"].items():
            hchecks = [entry.get("health_check"),
                       (entry.get("docs_server") or {}).get("health_check")]
            for check in hchecks:
                if not check or not check.get("harmless_call"):
                    continue
                name = check["harmless_call"]["name"].lower()
                for word in forbidden:
                    self.assertNotIn(word, name,
                                     f"{cid}: harmless op '{name}' is not harmless")


if __name__ == "__main__":
    unittest.main()
