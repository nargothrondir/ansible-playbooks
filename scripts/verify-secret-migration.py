#!/usr/bin/env python3
"""Compare every ansible-vault secret against its counterpart in OpenBao.

THIS IS THE CHECK TO RUN BEFORE DELETING THE ANSIBLE-VAULT FILES (#7, #2).
Until it reports zero discrepancies, the vault files are the only proof that
what OpenBao holds is what the fleet actually needs.

Run it on the panel, from the inventory checkout — it needs `ansible-vault`,
which lives there, and the `openbao` container:

    cd /opt/infra-inventory && python3 /opt/ansible-playbooks/scripts/verify-secret-migration.py

It asks for the vault password once per file. It prints variable names and
verdicts only: values are compared as truncated SHA-256, so nothing secret
reaches the terminal, the scrollback or a log.

Hashes rather than lengths, deliberately. Two different values of equal length
compare equal by length; on the first real run that mattered — telegram's
chat_id held `<id>:<topic>` in the vault against a correctly split pair in
OpenBao, and only the hash caught it.

WHEN A PAIR IS ADDED OR MIGRATED, UPDATE THE TABLES BELOW. A secret absent
from both MAP and SKIP is reported under "unaccounted", which is the whole
point: the migration was twice declared complete on the strength of grepping
the file that *references* secrets rather than the one that *holds* them.
"""

import hashlib
import json
import subprocess
import sys

import yaml

# vault variable -> where it now lives in OpenBao.
#   (group_vars group, variable name): (KV path under infra/, field)
MAP = {
    ("all", "vault_telegram_bot_token"): ("telegram", "bot_token"),
    ("all", "vault_telegram_chat_id"): ("telegram", "chat_id"),
    ("all", "vault_telegram_updates_topic_id"): ("telegram", "updates_topic_id"),
    ("all", "vault_netbird_setup_key"): ("netbird", "setup_key"),
    ("all", "vault_beszel_admin_email"): ("beszel", "admin_email"),
    ("all", "vault_beszel_admin_password"): ("beszel", "admin_password"),
    # No consumer yet: the dns role of #43 is unwritten. Migrated ahead of it so
    # the vault files are not held hostage to unstarted work.
    ("all", "vault_cloudflare_dns_token"): ("cloudflare", "dns_token"),
    ("control", "vault_remnawave_api_token"): ("remnawave", "api_token"),
    ("control", "vault_semaphore_api_token"): ("semaphore", "api_token"),
}

# hawser is the one table-shaped secret: fields are inventory hostnames.
HAWSER_VAR = "hawser_host_tokens"
HAWSER_PATH = "hawser"

# Present in the vault on purpose and NOT going to OpenBao. Each needs a reason.
SKIP = {
    # An address, not a credential. It belongs in plain group_vars once the
    # vault files go; moving it to a secret store would overstate what it is.
    "vault_remnawave_panel_url",
}

GROUPS = ("all", "control", "fleet")


def digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:12]


def read_vault(group):
    out = subprocess.run(
        ["ansible-vault", "view", f"group_vars/{group}/vault.yml"],
        capture_output=True, text=True, check=True,
    ).stdout
    return yaml.safe_load(out) or {}


def read_kv(path):
    out = subprocess.run(
        ["docker", "exec", "-i", "openbao", "bao", "kv", "get",
         "-format=json", f"infra/{path}"],
        capture_output=True, text=True,
    )
    if out.returncode:
        return None
    return json.loads(out.stdout)["data"]["data"]


def main():
    groups = {g: read_vault(g) for g in GROUPS}
    bad = 0

    for (group, var), (path, field) in sorted(MAP.items()):
        src = groups[group].get(var)
        dst = (read_kv(path) or {}).get(field)
        if src is None:
            verdict = "MISSING IN VAULT"
        elif dst is None:
            verdict = "MISSING IN OPENBAO"
        elif digest(src) != digest(dst):
            verdict = "MISMATCH"
        else:
            verdict = "ok"
        bad += verdict != "ok"
        print(f"  {var:<38} -> infra/{path}/{field:<18} {verdict}")

    table = groups["fleet"].get(HAWSER_VAR) or {}
    stored = read_kv(HAWSER_PATH) or {}
    for host in sorted(set(table) | set(stored)):
        if host not in table:
            verdict = "EXTRA IN OPENBAO"
        elif host not in stored:
            verdict = "MISSING IN OPENBAO"
        elif digest(table[host]) != digest(stored[host]):
            verdict = "MISMATCH"
        else:
            verdict = "ok"
        bad += verdict != "ok"
        print(f"  {HAWSER_VAR + '[' + host + ']':<38} "
              f"-> infra/{HAWSER_PATH}/{host:<14} {verdict}")

    known = {var for _, var in MAP} | SKIP | {HAWSER_VAR}
    unaccounted = sorted(
        v for g in groups.values() for v in g
        if v.startswith("vault_") and v not in known
    )

    print()
    print("kept in the vault on purpose:", ", ".join(sorted(SKIP)))
    print("unaccounted:                 ", ", ".join(unaccounted) or "none")
    if unaccounted:
        bad += len(unaccounted)

    print()
    print(f"DISCREPANCIES: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
