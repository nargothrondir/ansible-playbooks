"""Deterministic regression tests; no Cloudflare account or external network."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("warp_native", ROOT / "files/warp-native.py")
warp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(warp)


class MarkTests(unittest.TestCase):
    def test_exact_and_masked_conflicts(self):
        self.assertTrue(warp.mark_matches("51888"))
        self.assertTrue(warp.mark_matches("0xca00/0xff00"))
        self.assertFalse(warp.mark_matches("0x20000/0x20000"))
        self.assertFalse(warp.mark_matches("51889"))

    def test_nft_mask_and_dynamic_writers(self):
        meta = {"meta": {"key": "mark"}}
        self.assertTrue(warp.consumes_mark({"match": {"op": "==", "left": {"&": [meta, 0xff00]}, "right": 0xca00}}))
        self.assertFalse(warp.consumes_mark({"mangle": {"key": meta, "value": 0x20000}}))
        self.assertFalse(warp.consumes_mark({"mangle": {"key": meta, "value": {"|": [meta, 0x20000]}}}))
        self.assertTrue(warp.consumes_mark({"mangle": {"key": meta, "value": {"ct": {"key": "mark"}}}}))
        self.assertTrue(warp.consumes_mark({"match": {"op": "!=", "left": meta, "right": 0}}))
        self.assertFalse(warp.consumes_mark({"match": {"op": "!=", "left": meta, "right": 51888}}))

    def test_policy_rule_ownership_is_exact(self):
        rule = {"priority": 10088, "src": "all", "fwmark": "0xcab0", "table": 51888}
        self.assertTrue(warp.own_rule(rule))
        self.assertFalse(warp.own_rule(dict(rule, fwmask="0xff00")))
        self.assertFalse(warp.own_rule(dict(rule, dst="192.0.2.0/24")))
        self.assertFalse(warp.own_rule(dict(rule, table=254)))

    def test_foreign_nft_table_is_never_adopted(self):
        entries = [{"table": {"family": "inet", "name": "warp_native", "comment": "another owner"}}]
        with patch.object(warp, "owned", return_value=True), self.assertRaises(RuntimeError):
            warp.check_nft_ownership(entries)

    def test_missing_fib_table_can_have_partial_json(self):
        with patch.object(warp, "run", return_value=Mock(returncode=2, stdout="[", stderr="FIB table does not exist")):
            self.assertEqual(warp.routes(), [])

    def test_bookworm_ownership_without_table_comment(self):
        entries = [
            {"table": {"family": "inet", "name": "warp_native"}},
            {"chain": {"family": "inet", "table": "warp_native", "name": warp.OWNER_CHAIN}},
        ]
        with patch.object(warp, "owned", return_value=True):
            warp.check_nft_ownership(entries)
            with self.assertRaises(RuntimeError):
                warp.check_nft_ownership(entries[:1])


class PrivateStateTests(unittest.TestCase):
    def test_render_is_private_idempotent_and_whitelisted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Synthetic keys are generated at runtime and never stored in the repository.
            import base64
            key = base64.b64encode(os.urandom(32)).decode()
            (root / "wgcf-profile.conf").write_text(
                f"[Interface]\nPrivateKey = {key}\nAddress = 192.0.2.2/32, 2001:db8::2/128\n"
                "DNS = 1.1.1.1\nPostDown = unsafe-command\nMTU = 9999\n"
                f"[Peer]\nPublicKey = {key}\nEndpoint = 192.0.2.1:2408\nAllowedIPs = 0.0.0.0/0, ::/0\n"
            )
            settings = {"endpoint": "", "mtu": 1280, "keepalive": 25}
            with patch.object(warp, "STATE", root), patch.object(warp, "PROFILE", root / "warp.conf"):
                self.assertTrue(warp.render(settings))
                self.assertFalse(warp.render(settings))
                content = (root / "warp.conf").read_text()
                self.assertEqual((root / "warp.conf").stat().st_mode & 0o777, 0o600)
                self.assertIn("Table = off", content)
                self.assertNotIn("DNS", content)
                self.assertNotIn("PostDown", content)
                self.assertNotIn("2001:db8", content)
                self.assertNotIn("::/0", content)
                (root / "warp.conf").chmod(0o644)
                self.assertTrue(warp.render(settings))
                self.assertFalse(warp.render(settings))


class ProbeTests(unittest.TestCase):
    def test_trace_must_explicitly_confirm_warp(self):
        for status, body, expected in [
            (200, b"warp=on\n", True), (200, b"warp=plus\n", True),
            (200, b"warp=off\n", False), (200, b"warp=only\n", False),
            (503, b"warp=on\n", False), (200, b"no trace\n", False),
        ]:
            with self.subTest(status=status, body=body):
                connection = Mock()
                connection.getresponse.return_value.status = status
                connection.getresponse.return_value.read.return_value = body
                with patch.object(warp, "WarpConnection", return_value=connection):
                    self.assertEqual(warp.probe(2), expected)

    def test_socket_is_marked_and_bound_before_connect(self):
        sock, context = Mock(), Mock()
        with patch.object(warp.socket, "socket", return_value=sock):
            connection = warp.WarpConnection(warp.PROBE_HOST, timeout=2, context=context)
            connection.connect()
        sock.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_MARK, 51888)
        sock.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b"warp\0")
        context.wrap_socket.assert_called_once_with(sock, server_hostname=warp.PROBE_HOST)

    def test_watchdog_cooldown_and_maintenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = {"timeout": 2, "cooldown": 180}
            with patch.object(warp, "CONFIG", root), patch.object(warp, "RUNTIME", root), \
                    patch.object(warp.subprocess, "run", return_value=Mock(returncode=1)), \
                    patch.object(warp, "run") as restart:
                warp.watchdog(settings)
                warp.watchdog(settings)
                restart.assert_called_once_with("systemctl", "restart", "wg-quick@warp.service")
                (root / "watchdog.disabled").touch()
                warp.watchdog(settings)
                self.assertEqual(restart.call_count, 1)

    def test_healthy_exit_never_restarts_even_with_an_old_handshake(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(warp, "CONFIG", Path(directory)), \
                patch.object(warp.subprocess, "run", return_value=Mock(returncode=0)), \
                patch.object(warp, "run") as restart:
            warp.watchdog({"timeout": 2, "cooldown": 180})
            restart.assert_not_called()

    def test_probe_timeout_triggers_bounded_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(warp, "CONFIG", root), patch.object(warp, "RUNTIME", root), \
                    patch.object(warp.subprocess, "run", side_effect=subprocess.TimeoutExpired("probe", 3)), \
                    patch.object(warp, "run") as restart:
                warp.watchdog({"timeout": 2, "cooldown": 180})
                self.assertEqual(restart.call_count, 1)


class XrayTemplateTests(unittest.TestCase):
    def test_only_opted_in_profiles_have_a_marked_outbound(self):
        import jinja2
        environment = jinja2.Environment()
        environment.filters["bool"] = bool
        template = environment.from_string(
            (ROOT.parents[1] / "playbooks/templates/xray-reality-profile.json.j2").read_text()
        )
        for enabled in (False, True):
            data = json.loads(template.render(profile_use_warp=enabled,
                profile_inbound_tag="test", profile_short_id="test", profile_private_key="test", profile_domain="example.com"))
            outbound = [item for item in data["outbounds"] if item["tag"] == "warp-out"]
            self.assertEqual(len(outbound), int(enabled))
            if enabled:
                self.assertEqual(outbound[0]["settings"]["domainStrategy"], "ForceIPv4")
                self.assertEqual(outbound[0]["streamSettings"]["sockopt"]["mark"], 51888)
                self.assertEqual(outbound[0]["streamSettings"]["sockopt"]["interface"], "warp")


if __name__ == "__main__":
    unittest.main()
