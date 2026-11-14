#!/usr/bin/python3
"""Host-local WARP state. Never print profiles, keys, accounts or remote addresses."""

import configparser
import fcntl
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time


MARK = 51888
RULE_PRIORITY = 10088
TABLE = "warp_native"
OWNER = "ansible warp_native v1"
OWNER_CHAIN = "ansible_warp_native_v1"
PROBE_HOST = "1.1.1.1"
STATE = Path("/var/lib/warp-native")
CONFIG = Path("/etc/warp-native")
PROFILE = Path("/etc/wireguard/warp.conf")
RUNTIME = Path("/run/warp-native")
HELPER = "/usr/local/libexec/warp-native"
UNREACHABLE_METRIC = 42760


def run(*args, allowed=(0,), **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, timeout=40, **kwargs)
    if result.returncode not in allowed:
        # Command output may contain private material or fleet addresses.
        raise RuntimeError(f"{Path(args[0]).name} failed (exit {result.returncode})")
    return result


def number(value):
    if isinstance(value, int):
        return value
    return int(str(value), 16 if str(value).startswith("0x") else 10)


def mark_matches(value):
    """An exact mark or a masked match/assignment might consume our mark."""
    parts = str(value).split("/")
    mask = number(parts[1]) if len(parts) == 2 else 0xFFFFFFFF
    return MARK & mask == number(parts[0]) & mask


def owned():
    marker = CONFIG / "owner"
    return marker.is_file() and not marker.is_symlink() and marker.read_text().strip() == OWNER


def rules(family="-4"):
    return json.loads(run("ip", family, "-j", "rule", "show").stdout)


def own_rule(rule):
    # iproute2 omits the full fwmask on some versions and prints it on others.
    return (
        rule.get("priority") == RULE_PRIORITY
        and rule.get("src") == "all"
        and str(rule.get("table")) == str(MARK)
        and number(rule.get("fwmark", -1)) == MARK
        and number(rule.get("fwmask", 0xFFFFFFFF)) == 0xFFFFFFFF
        and not (set(rule) - {"priority", "src", "table", "fwmark", "fwmask", "protocol"})
    )


def routes():
    result = run("ip", "-4", "-j", "route", "show", "table", str(MARK), allowed=(0, 2))
    if result.returncode == 2 and "FIB table does not exist" not in result.stderr:
        raise RuntimeError("Cannot inspect the reserved routing table")
    if result.returncode == 2:
        # bookworm iproute2 can emit a partial '[' before reporting no table.
        return []
    return json.loads(result.stdout or "[]")


def own_route(route):
    return route.get("dst") == "default" and (
        (route.get("type") == "unreachable" and route.get("metric") == UNREACHABLE_METRIC)
        or (route.get("dev") == "warp" and route.get("metric") == 10 and "gateway" not in route)
    )


def nft_state():
    if not shutil.which("nft"):
        return []
    return json.loads(run("nft", "-j", "list", "ruleset").stdout)["nftables"]


def is_mark(expr):
    return expr in ({"meta": {"key": "mark"}}, {"ct": {"key": "mark"}})


def may_equal(expr, value):
    if isinstance(expr, (int, str)):
        try:
            return value == number(expr)
        except ValueError:
            return True
    if isinstance(expr, list):
        return any(may_equal(item, value) for item in expr)
    if isinstance(expr, dict):
        if "range" in expr:
            return number(expr["range"][0]) <= value <= number(expr["range"][1])
        if "set" in expr:
            return may_equal(expr["set"], value)
        # Constant bitwise expressions can exclude our value even if their
        # input is dynamic (e.g. NetBird reserves a disjoint high bit).
        for op in ("|", "&", "^"):
            if op in expr:
                left, right = expr[op]
                if isinstance(right, int):
                    if op == "|" and value & right != right:
                        return False
                    if op == "&" and value & ~right:
                        return False
                    if op == "^":
                        return may_equal(left, value ^ right)
        return True
    return True


def consumes_mark(expr):
    """Conservatively reject unknown dynamic mark writers and matching readers."""
    if isinstance(expr, list):
        return any(consumes_mark(item) for item in expr)
    if not isinstance(expr, dict):
        return False
    if "mangle" in expr and is_mark(expr["mangle"].get("key")):
        return may_equal(expr["mangle"].get("value"), MARK)
    if "match" in expr:
        match = expr["match"]
        left, right = match.get("left"), match.get("right")
        if is_mark(left):
            return comparison_consumes(right, MARK, match.get("op"))
        if isinstance(left, dict) and "&" in left and is_mark(left["&"][0]):
            return comparison_consumes(right, MARK & number(left["&"][1]), match.get("op"))
        if is_mark(right):
            return may_equal(left, MARK)
    return any(consumes_mark(value) for value in expr.values())


def comparison_consumes(expression, value, operator):
    if operator in ("==", "in"):
        return may_equal(expression, value)
    try:
        expected = number(expression)
    except (ValueError, TypeError):
        return True
    if operator == "!=":
        return value != expected
    if operator == "<":
        return value < expected
    if operator == ">":
        return value > expected
    if operator == "<=":
        return value <= expected
    if operator == ">=":
        return value >= expected
    return True


def check_nft_ownership(entries):
    for entry in entries:
        table = entry.get("table", {})
        if table.get("family") == "inet" and table.get("name") == TABLE:
            marker_chain = any(
                e.get("chain", {}).get("family") == "inet"
                and e["chain"].get("table") == TABLE
                and e["chain"].get("name") == OWNER_CHAIN for e in entries
            )
            # nft 1.0.6 (bookworm) omits table comments from its JSON output.
            owner_matches = table.get("comment") == OWNER or ("comment" not in table and marker_chain)
            if not owned() or not owner_matches:
                raise RuntimeError("The reserved nftables table belongs to another installation")


def preflight():
    ownership = owned()
    if (CONFIG / "owner").exists() and not ownership:
        raise RuntimeError("Unknown WARP ownership marker")
    if not ownership and any(path.exists() for path in (
        CONFIG, PROFILE, Path(HELPER), Path("/usr/local/lib/warp-native"),
        Path("/etc/systemd/system/warp-native-guard.service"),
        Path("/etc/systemd/system/warp-native-watchdog.service"),
        Path("/etc/systemd/system/warp-native-watchdog.timer"),
        Path("/etc/systemd/system/wg-quick@warp.service.d/50-warp-native.conf"),
        Path("/etc/systemd/system/nftables.service.d/50-warp-native.conf"),
    )):
        raise RuntimeError("Unmanaged WARP files exist; migrate them explicitly before using this role")
    for family in ("-4", "-6"):
        for rule in rules(family):
            if ownership and family == "-4" and own_rule(rule):
                continue
            mask = number(rule.get("fwmask", 0xFFFFFFFF))
            if rule.get("priority") == RULE_PRIORITY or (
                "fwmark" in rule and MARK & mask == number(rule["fwmark"]) & mask
            ):
                raise RuntimeError("Routing mark 51888 or rule priority 10088 is already in use")
            if str(rule.get("table")) == str(MARK):
                raise RuntimeError("Routing table 51888 has another policy consumer")
            if (family == "-4" and rule.get("table") in ("main", 254)
                    and rule.get("priority", 32766) < RULE_PRIORITY
                    and set(rule) <= {"priority", "src", "table", "protocol"}):
                raise RuntimeError("An earlier unconditional main-table lookup would shadow the WARP policy")
    if any(not ownership or not own_route(route) for route in routes()):
        raise RuntimeError("Routing table 51888 is already in use")
    entries = nft_state()
    check_nft_ownership(entries)
    for entry in entries:
        rule = entry.get("rule", {})
        if rule.get("family") == "inet" and rule.get("table") == TABLE:
            continue
        if consumes_mark(rule.get("expr", [])):
            raise RuntimeError("A foreign nftables mark expression may consume 51888; review it first")
    # Include iptables-legacy installations, which nft JSON cannot see.
    for binary in ("iptables-save", "ip6tables-save", "iptables-legacy-save", "ip6tables-legacy-save"):
        if not shutil.which(binary):
            continue
        for line in run(binary).stdout.splitlines():
            tokens = shlex.split(line)
            for index, token in enumerate(tokens):
                if token in ("--mark", "--set-mark", "--set-xmark", "--set-return"):
                    matches = mark_matches(tokens[index + 1])
                    if token == "--mark" and index > 0 and tokens[index - 1] == "!":
                        matches = not matches
                    if matches:
                        raise RuntimeError("A foreign iptables rule consumes mark 51888")
                if token in ("--or-mark", "--and-mark", "--xor-mark", "--restore-mark"):
                    raise RuntimeError("A dynamic iptables mark writer requires review before reserving 51888")
    if shutil.which("wg"):
        for line in run("wg", "show", "all", "fwmark").stdout.splitlines():
            if line.split()[-1] != "off" and mark_matches(line.split()[-1]):
                raise RuntimeError("A WireGuard transport already uses mark 51888")
    if not ownership and run("ip", "link", "show", "dev", "warp", allowed=(0, 1)).returncode == 0:
        raise RuntimeError("An unmanaged warp interface already exists")
    print("ok")


def nft_correct(entries):
    tables = [e["table"] for e in entries if "table" in e
              and e["table"].get("family") == "inet" and e["table"].get("name") == TABLE]
    chains = [e["chain"] for e in entries if "chain" in e
              and e["chain"].get("family") == "inet" and e["chain"].get("table") == TABLE]
    nft_rules = [e["rule"] for e in entries if "rule" in e
                 and e["rule"].get("family") == "inet" and e["rule"].get("table") == TABLE]
    if len(tables) != 1 or len(chains) != 2 or len(nft_rules) != 1:
        return False
    output_chains = [chain for chain in chains if chain.get("name") == "output"]
    if len(output_chains) != 1 or not any(chain.get("name") == OWNER_CHAIN and "hook" not in chain for chain in chains):
        return False
    chain, rule = output_chains[0], nft_rules[0]
    expressions = [{"counter": None} if "counter" in e else e for e in rule["expr"]]
    return (
        chain.get("name") == "output" and chain.get("type") == "filter"
        and chain.get("hook") == "output" and chain.get("prio") == -10
        and chain.get("policy") == "accept" and rule.get("chain") == "output"
        and rule.get("comment") == OWNER
        and expressions == [
            {"match": {"op": "==", "left": {"meta": {"key": "mark"}}, "right": MARK}},
            {"match": {"op": "!=", "left": {"meta": {"key": "oifname"}}, "right": "warp"}},
            {"counter": None}, {"drop": None},
        ]
    )


def ensure():
    if not owned():
        raise RuntimeError("Refusing to manage WARP without ownership")
    entries = nft_state()
    check_nft_ownership(entries)
    changed = False
    if not nft_correct(entries):
        exists = any(e.get("table", {}).get("family") == "inet"
                     and e.get("table", {}).get("name") == TABLE for e in entries)
        batch = f"delete table inet {TABLE}\n" if exists else ""
        batch += f'''table inet {TABLE} {{
 comment "{OWNER}"
 chain {OWNER_CHAIN} {{ }}
 chain output {{
  type filter hook output priority -10; policy accept;
  meta mark {MARK} oifname != "warp" counter drop comment "{OWNER}"
 }}
}}
'''
        # The delete/recreate is a single atomic transaction, confined to our table.
        run("nft", "-f", "-", input=batch)
        changed = True
    current_routes = routes()
    if any(not own_route(route) for route in current_routes):
        raise RuntimeError("Refusing to replace foreign routes in table 51888")
    if not any(route.get("type") == "unreachable" for route in current_routes):
        run("ip", "-4", "route", "add", "unreachable", "default", "table", str(MARK),
            "metric", str(UNREACHABLE_METRIC))
        changed = True
    current_rules = rules()
    if any(r.get("priority") == RULE_PRIORITY and not own_rule(r) for r in current_rules):
        raise RuntimeError("Refusing to replace a foreign policy rule")
    if not any(own_rule(rule) for rule in current_rules):
        run("ip", "-4", "rule", "add", "priority", str(RULE_PRIORITY), "fwmark", str(MARK),
            "lookup", str(MARK))
        changed = True
    if run("ip", "link", "show", "dev", "warp", allowed=(0, 1)).returncode == 0:
        if not any(route.get("dev") == "warp" for route in current_routes):
            run("ip", "-4", "route", "add", "default", "dev", "warp", "table", str(MARK), "metric", "10")
            changed = True
    return changed


def remove():
    if not owned():
        raise RuntimeError("Refusing removal without ownership")
    changed = False
    for rule in rules():
        if own_rule(rule):
            run("ip", "-4", "rule", "del", "priority", str(RULE_PRIORITY), "fwmark", str(MARK), "lookup", str(MARK))
            changed = True
    for route in routes():
        if not own_route(route):
            raise RuntimeError("Refusing removal of a foreign route")
        args = ["unreachable", "default"] if route.get("type") == "unreachable" else ["default", "dev", "warp"]
        run("ip", "-4", "route", "del", *args, "table", str(MARK), "metric", str(route["metric"]))
        changed = True
    entries = nft_state()
    check_nft_ownership(entries)
    if any(e.get("table", {}).get("family") == "inet"
           and e.get("table", {}).get("name") == TABLE for e in entries):
        run("nft", "delete", "table", "inet", TABLE)
        changed = True
    return changed


def atomic_private(path, content):
    if path.is_file() and path.read_text() == content:
        changed = path.stat().st_mode & 0o777 != 0o600
        os.chmod(path, 0o600)
        return changed
    fd, temp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return True


def render(settings):
    profile = configparser.ConfigParser(interpolation=None, strict=True)
    profile.read(STATE / "wgcf-profile.conf")
    interface, peer = profile["Interface"], profile["Peer"]
    addresses = [str(ipaddress.ip_interface(addr.strip())) for addr in interface["Address"].split(",")
                 if ipaddress.ip_interface(addr.strip()).version == 4]
    if len(addresses) != 1:
        raise RuntimeError("The generated profile must contain exactly one IPv4 address")
    endpoint, port = (settings["endpoint"] or peer["Endpoint"]).rsplit(":", 1)
    if not re.fullmatch(r"[A-Za-z0-9.-]+", endpoint) or not 1 <= int(port) <= 65535:
        raise RuntimeError("WARP requires an IPv4-capable endpoint and valid port")
    # Pin the initial IPv4 selection so DNS answer rotation cannot restart a
    # healthy tunnel on every Ansible run. Changing the endpoint invalidates it.
    source = f"{endpoint}:{port}"
    cache_path = STATE / "endpoint.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    if cache.get("source") == source:
        endpoint = str(ipaddress.IPv4Address(cache["address"]))
    else:
        endpoints = sorted({entry[4][0] for entry in socket.getaddrinfo(endpoint, int(port),
                            socket.AF_INET, socket.SOCK_DGRAM)})
        if not endpoints:
            raise RuntimeError("WARP endpoint has no IPv4 address")
        endpoint = endpoints[0]
        atomic_private(cache_path, json.dumps({"source": source, "address": endpoint}))
    private_key, public_key = interface["PrivateKey"], peer["PublicKey"]
    if not all(re.fullmatch(r"[A-Za-z0-9+/]{43}=", key) for key in (private_key, public_key)):
        raise RuntimeError("Invalid WireGuard key format")
    # Whitelist fields instead of copying wgcf hooks/DNS/IPv6 into the live config.
    content = f'''# Managed by Ansible warp_native; private state remains on this node.
[Interface]
PrivateKey = {private_key}
Address = {addresses[0]}
MTU = {int(settings['mtu'])}
Table = off
PostUp = {HELPER} ensure

[Peer]
PublicKey = {public_key}
AllowedIPs = 0.0.0.0/0
Endpoint = {endpoint}:{port}
PersistentKeepalive = {int(settings['keepalive'])}
'''
    return atomic_private(PROFILE, content)


class WarpConnection(http.client.HTTPSConnection):
    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_MARK, MARK)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b"warp\0")
            # A numeric destination avoids using the host or Xray resolver.
            sock.connect(("1.1.1.1", 443))
            self.sock = self._context.wrap_socket(sock, server_hostname=PROBE_HOST)
        except Exception:
            sock.close()
            raise


def probe(timeout):
    connection = WarpConnection(PROBE_HOST, timeout=timeout, context=ssl.create_default_context())
    try:
        connection.request("GET", "/cdn-cgi/trace", headers={"Connection": "close"})
        response = connection.getresponse()
        body = response.read(65536).decode("ascii", errors="replace")
        return response.status == 200 and any(line in ("warp=on", "warp=plus") for line in body.splitlines())
    except (OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def watchdog(settings):
    if (CONFIG / "watchdog.disabled").exists():
        return
    # Interface-bound, marked HTTPS with certificate verification; handshake age
    # is deliberately irrelevant. No ICMP or a mere TCP connection counts as health.
    try:
        healthy = subprocess.run([sys.executable, HELPER, "probe"], capture_output=True,
                                 timeout=settings["timeout"] + 1).returncode == 0
    except subprocess.TimeoutExpired:
        healthy = False
    if healthy:
        print("WARP egress is healthy")
        return
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    timestamp = RUNTIME / "last-restart"
    now = time.monotonic()
    if timestamp.exists() and now - float(timestamp.read_text()) < settings["cooldown"]:
        print("WARP recovery is cooling down")
        return
    # Record attempts, including failed starts, to avoid hammering an unavailable peer.
    atomic_private(timestamp, str(now))
    print("WARP egress failed; attempting interface recovery", flush=True)
    run("systemctl", "restart", "wg-quick@warp.service")


def main():
    os.umask(0o077)
    command = sys.argv[1]
    if command == "preflight":
        preflight()
        return
    if command in ("register", "generate"):
        run("/usr/local/lib/warp-native/wgcf", command,
            *(["--accept-tos"] if command == "register" else []), cwd=STATE)
        return
    if command == "probe":
        settings = json.loads((CONFIG / "settings.json").read_text())
        sys.exit(0 if probe(settings["timeout"]) else 1)
    # Serialize PostUp, firewall reloads, Ansible and timer attempts on the node.
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    # The watchdog must not hold the guard's lock while waiting for systemctl:
    # wg-quick's ExecStartPre and PostUp acquire that lock themselves.
    lock_name = "watchdog.lock" if command == "watchdog" else "lock"
    with (RUNTIME / lock_name).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if command in ("ensure", "remove"):
            changed = ensure() if command == "ensure" else remove()
            print("changed" if changed else "ok")
        elif command == "render":
            print("changed" if render(json.loads((CONFIG / "settings.json").read_text())) else "ok")
        elif command == "watchdog":
            watchdog(json.loads((CONFIG / "settings.json").read_text()))
        else:
            raise RuntimeError("Unknown WARP helper command")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Profile parser errors and CLI stderr can contain private key material.
        # Only our explicitly sanitized RuntimeErrors may reach the journal.
        print(str(error) if isinstance(error, RuntimeError) else f"WARP operation failed: {type(error).__name__}", file=sys.stderr)
        sys.exit(1)
