"""Real nftables/routing tests in a disposable container, using veth for warp.

This deliberately does not claim to test WireGuard, WARP, systemd or Xray.
"""

import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import urllib.request


loader = importlib.machinery.SourceFileLoader("warp_native", "/usr/local/libexec/warp-native")
spec = importlib.util.spec_from_loader(loader.name, loader)
warp = importlib.util.module_from_spec(spec)
loader.exec_module(warp)


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def direct():
    url = "http://" + os.environ["TEST_RECEIVER"] + ":8080/"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    assert opener.open(url, timeout=3).status == 200


def drop_count():
    data = json.loads(command("nft", "-j", "list", "table", "inet", "warp_native"))
    return sum(expr["counter"]["packets"] for item in data["nftables"]
               for expr in item.get("rule", {}).get("expr", []) if "counter" in expr)


warp.CONFIG.mkdir(mode=0o700)
(warp.CONFIG / "owner").write_text(warp.OWNER + "\n")
resolver_before = Path("/etc/resolv.conf").read_bytes()
baseline = command("ip", "-4", "route", "show", "table", "main")
command("nft", "add", "table", "inet", "foreign_test")
warp.preflight()
command("ip", "-4", "rule", "add", "priority", "20", "fwmark", "0xca00/0xff00", "lookup", "main")
try:
    warp.preflight()
    raise AssertionError("A masked mark collision was not rejected")
except RuntimeError:
    pass
command("ip", "-4", "rule", "del", "priority", "20", "fwmark", "0xca00/0xff00", "lookup", "main")
assert warp.ensure()
assert not warp.ensure(), "Guard must converge without resetting counters"
direct()

# A simulated tunnel provides a route, without requiring a kernel WG module.
command("ip", "link", "add", "warp", "type", "veth", "peer", "name", "warp-peer")
command("ip", "link", "set", "warp", "up")
command("ip", "link", "set", "warp-peer", "up")
assert warp.ensure()
assert not warp.ensure()
route = json.loads(command("ip", "-4", "-j", "route", "get", "1.1.1.1", "mark", "51888"))
assert route[0]["dev"] == "warp"
assert command("ip", "-4", "route", "show", "table", "main") == baseline
direct()

# Losing the interface must leave both nftables and the unreachable route intact.
command("ip", "link", "delete", "warp")
assert not warp.ensure()
blocked = subprocess.run(["ip", "-4", "route", "get", "1.1.1.1", "mark", "51888"], capture_output=True)
assert blocked.returncode != 0
assert warp.nft_correct(warp.nft_state())
direct()

# Force a marked socket toward the ordinary interface to exercise the actual
# nft drop independently of the second layer provided by policy routing.
command("ip", "-4", "rule", "add", "priority", "10", "fwmark", "51888", "lookup", "main")
before = drop_count()
with socket.socket() as sock:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_MARK, warp.MARK)
    sock.settimeout(1)
    try:
        sock.connect((os.environ["TEST_RECEIVER"], 8080))
        raise AssertionError("Marked traffic leaked through the ordinary interface")
    except (TimeoutError, OSError):
        pass
assert drop_count() > before
direct()
command("ip", "-4", "rule", "del", "priority", "10", "fwmark", "51888", "lookup", "main")

# Simulate loss of the owned table during a firewall reload, then reconcile.
command("nft", "delete", "table", "inet", "warp_native")
blocked = subprocess.run(["ip", "-4", "route", "get", "1.1.1.1", "mark", "51888"], capture_output=True)
assert blocked.returncode != 0, "Policy routing must remain closed while nft rules are being restored"
direct()
assert warp.ensure()
assert not warp.ensure()
command("nft", "list", "table", "inet", "foreign_test")
assert Path("/etc/resolv.conf").read_bytes() == resolver_before
assert command("ip", "-4", "route", "show", "table", "main") == baseline
command("ip", "link", "add", "warp", "type", "veth", "peer", "name", "warp-peer")
command("ip", "link", "set", "warp", "up")
command("ip", "link", "set", "warp-peer", "up")
assert warp.ensure()
assert not warp.ensure()
route = json.loads(command("ip", "-4", "-j", "route", "get", "1.1.1.1", "mark", "51888"))
assert route[0]["dev"] == "warp", "Marked routing must recover with the interface"
command("ip", "link", "delete", "warp")
assert warp.remove()
assert not warp.remove()
command("nft", "list", "table", "inet", "foreign_test")
direct()
print("PASS: idempotent guard, selective routing, real nft drop, direct egress, table repair and scoped removal")
