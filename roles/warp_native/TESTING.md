# Selective WARP verification

## Running through Semaphore

The working branch must be published before Semaphore can fetch these files.
Changing the shared Repository record from main is not required. Publishing
the branch makes the source available; it does not create UI templates or
run tasks on nodes.

Run `playbooks/semaphore-template.yml`, then `playbooks/semaphore-survey.yml`
from `feat/warp-native`, using the existing private inventory and the Variable
Group required by those management playbooks. Both management runs target
`controller`: leave Limit empty. The existing UI templates are named
`Semaphore: Sync templates` and `Semaphore: Sync surveys`; select the feature
branch at launch if those templates permit a branch override. Otherwise use
an ad-hoc bootstrap template for the management playbook on the feature branch,
as described in the management playbooks' headers, without editing the shared
Repository record.

Expected: `Node: Configure WARP` appears under Nodes, with a required
`warp_native_target` survey field and Git branch `feat/warp-native`.
Fill the field with one exact lab inventory hostname and leave Limit empty.
First launch with `--check` and `--diff` in CLI args. Then launch twice with
those arguments removed; expect `changed=0` on the second real run. The role
already declares privilege escalation in its playbook; keep the working
inventory's SSH/sudo credentials. This task never calls the Remnawave API.

The node-local `sudo` commands and client `curl` commands below remain valid
when installation is launched from Semaphore. The CLI Ansible commands are
alternatives for a controller terminal, not commands to paste into Semaphore's
CLI args field. For rollback use the same UI template with
`-e warp_native_state=absent`, after removing test-profile WARP references.

## Local checks

From the repository root, with Ansible, the pinned collections from
`requirements.yml`, Python/Jinja2, Docker and a container runtime allowing
`NET_ADMIN`:

```bash
ansible-galaxy collection install -r requirements.yml
for playbook in playbooks/*.yml; do
  ansible-playbook -i inventory/hosts.example.yml --syntax-check "$playbook" || exit 1
done
ansible-lint
bash .github/scripts/spec-guards.sh
bash .github/scripts/tells-guard.sh
python3 -m unittest discover -s roles/warp_native/tests -v
bash roles/warp_native/tests/run-network-tests.sh bookworm
bash roles/warp_native/tests/run-network-tests.sh trixie
```

Expected: syntax/lint/guards and unit tests pass; both network runs end with
`PASS`. The containers exercise actual Linux policy routing and nft drops,
unmarked HTTP egress to a separate receiver, removal and table-loss repair.
They use a disposable **veth** named `warp`; they do not register Cloudflare
devices or prove WireGuard encryption, WARP connectivity or Xray behavior.
The existing repository scenario is run separately:

```bash
cd roles/bootstrap
molecule test
```

Expected: convergence, idempotence and verification succeed on Debian 13.

## Xray fragment and DNS

Append this outbound to the **test** profile; keep `DIRECT` first (the current
repository's default). Put the domain rule before broad direct rules. Never
add a balancer `fallbackTag`, proxy fallback or client node failover for this
test: a failed selected request must remain failed.

```json
{
  "outbounds": [
    { "tag": "DIRECT", "protocol": "freedom" },
    {
      "tag": "warp-out",
      "protocol": "freedom",
      "settings": { "domainStrategy": "ForceIPv4" },
      "streamSettings": {
        "sockopt": { "interface": "warp", "mark": 51888 }
      }
    }
  ],
  "routing": {
    "rules": [
      {
        "type": "field",
        "domain": ["domain:example.com", "full:www.cloudflare.com"],
        "outboundTag": "warp-out"
      }
    ]
  }
}
```

This is a fragment to merge, not a replacement for the complete profile:
retain the existing private-address/BitTorrent blocks and other inbounds and
outbounds. Replace `domain:example.com` with the chosen domain list. The full
Cloudflare name is included solely to make the trace acceptance test repeatable.
Do not apply this to a live shared profile during this implementation task.

The repository **does** manage profile creation in `playbooks/new-profile.yml`
and `playbooks/templates/xray-reality-profile.json.j2`. The optional
`profile_use_warp` branch is now marked/IPv4-only; it remains off by default.
The role never calls the panel or re-applies that playbook. Existing profiles
must be reviewed separately before enabling WARP in the panel.

`ForceIPv4` resolves outbound domain targets through Xray's built-in DNS and
requires an IPv4 result. The current template sets DoH
`https://dns.google/dns-query`, `queryStrategy: UseIPv4` and
`skipFallback: false`. Routing domains require domain names to reach Xray
(for example SOCKS5 hostname mode or the existing TLS/HTTP sniffing).
Neither `sockopt.interface` nor the kill switch automatically marks DNS
requests made by Xray's DNS subsystem. DoH normally follows its own routing
decision; a bootstrap lookup may use the system resolver. DNS-through-WARP
requires a separate reviewed DNS configuration/routing policy and testing.
No such policy or resolver change is included here.

## Validation performed in this workspace (2026-11-14)

- Syntax-check: all 35 playbooks passed; the new playbook was checked again after role edits.
- Repository-wide ansible-lint: production profile passed with zero rule warnings/failures.
- All 14 spec guards, the de-identification guard and `git diff --check` passed.
- Thirteen unit regressions passed, including secret-file permissions, profile
  rendering, masked mark conflicts, timeout/cooldown behavior and the Xray template.
- Both Debian 12/13 container network suites passed: real nft drops, unaffected
  direct HTTP, policy-table recovery, an unreachable route during table loss,
  repeated reconciliation without changes and removal preserving a foreign table.
- Initial `--check --diff` passed in a Debian 12 container with synthetic
  systemd facts, python3-apt and the environment's trusted CA bundle. It did
  not execute systemd or account registration. Full-role convergence was not tested.
- Rendered units/drop-ins passed `systemd-analyze verify --man=no` against
  Debian's installed wg-quick/nftables units. This is static validation only.
- Both downloaded wgcf architecture binaries matched the pinned SHA-256 values;
  amd64 `register --help` confirmed `--accept-tos`. No device was registered.
- The existing bootstrap `molecule test` was attempted; container preparation
  failed because `deb.debian.org:80` was unreachable. Its convergence/idempotence
  did not execute. No existing scenario or check was weakened to bypass this.

## Before testing on a VPS

No reachable lab inventory, VPS credentials or WireGuard-capable test VPS was
available in this session. **The three real Xray/WARP states below were not
executed.** Full-role second-run idempotence, boot ordering, firewall service
reloads and account registration also remain to verify on that node. Local
network tests exercise the guard's second-run idempotence, not the whole role.

The source inspected in `docker-stacks/remnanode/docker-compose.yml` has
`network_mode: host`, `cap_add: [NET_ADMIN]`, and no configured capability drop
or user override. That establishes the intended container settings, not the
effective capabilities of a running Xray child. On the test node:

```bash
docker inspect -f '{{.HostConfig.NetworkMode}} {{json .HostConfig.CapAdd}} {{json .HostConfig.CapDrop}} {{.Config.User}}' remnanode
docker top remnanode -eo pid,comm
```

Expected: `host`, `NET_ADMIN`, no relevant drops; identify the Xray PID from
the second command. Set `XRAY_PID` to that numeric host PID, then:

```bash
XRAY_PID=12345
sudo python3 - "$XRAY_PID" <<'PY'
import pathlib, sys
p = pathlib.Path('/proc') / sys.argv[1]
caps = int(next(line.split()[1] for line in (p / 'status').read_text().splitlines()
                if line.startswith('CapEff:')), 16)
assert (p / 'ns/net').readlink() == pathlib.Path('/proc/1/ns/net').readlink()
assert caps & ((1 << 12) | (1 << 13)), 'SO_MARK requires NET_ADMIN or, on modern Linux, NET_RAW'
print('PASS: host network namespace and a SO_MARK capability are present')
PY
```

Expected: `PASS`. The PID is a placeholder, not a known process. A failure
requires investigation, not automatically adding capabilities. The end-to-end
request below confirms that Xray actually sets the options successfully.

Run installation twice using the README's single-host commands. Verify
`changed=0` on the second run. Compare main routes/defaults and NetBird status
before and after; use the same mesh session for the failure test. Check the
actual firewall entry points without dumping secret configuration:

```bash
sudo systemctl cat nftables.service
sudo systemctl is-active ufw crowdsec-firewall-bouncer
sudo ip -4 rule show
sudo ip -4 route show table 51888
sudo nft list table inet warp_native
netbird status
```

Expected: vendor commands remain, the role's appended hooks are visible;
existing firewall services retain their previous state; table 51888 contains
the tunnel and unreachable defaults. Inspecting rules/routes can show fleet
addresses: keep that output local and out of git.

## State 1: healthy WARP

Use a test Xray client connected exclusively to this one test node/profile,
with its local SOCKS5 listener on `127.0.0.1:10808`. Run the following on the
client workstation (change that listener address if necessary):

```bash
set -euo pipefail
XRAY_SOCKS=127.0.0.1:10808
curl -fsS --noproxy '' --proxy "socks5h://$XRAY_SOCKS" --max-time 20 \
  https://www.cloudflare.com/cdn-cgi/trace | sed -n '/^ip=/p;/^warp=/p'
curl -fsS --noproxy '' --proxy "socks5h://$XRAY_SOCKS" --max-time 20 \
  https://1.1.1.1/cdn-cgi/trace | sed -n '/^ip=/p;/^warp=/p'
```

Expected: selected hostname gives `warp=on` or `warp=plus` and a Cloudflare
WARP egress IP; numeric destination uses `DIRECT`, gives `warp=off` and the
VPS's ordinary egress IP. The `socks5h` URL preserves the hostname for Xray.
Do not infer success solely from a handshake or the interface state.

## State 2: stopped interface, no fallback

On the test node, first stop the watchdog and any running check, then WARP:

```bash
sudo touch /etc/warp-native/watchdog.disabled
sudo systemctl stop warp-native-watchdog.timer warp-native-watchdog.service
sudo systemctl stop wg-quick@warp
sudo nft list table inet warp_native
sudo ip -4 route show table 51888
```

Expected: nft drop still present, unreachable default retained, no `warp` link.
On the client workstation, using the same `XRAY_SOCKS` variable:

```bash
if curl -fsS --noproxy '' --proxy "socks5h://$XRAY_SOCKS" --max-time 15 \
  https://www.cloudflare.com/cdn-cgi/trace; then
  echo 'FAIL: selected traffic still succeeded' >&2
  exit 1
else
  echo 'PASS: selected traffic failed'
fi
curl -fsS --noproxy '' --proxy "socks5h://$XRAY_SOCKS" --max-time 20 \
  https://1.1.1.1/cdn-cgi/trace | sed -n '/^ip=/p;/^warp=/p'
```

Expected: selected request fails within the timeout; direct still reports the
ordinary VPS IP and `warp=off`. The unreachable route can reject a packet
before nft output, so an unchanged drop counter does not imply leakage.
From the controller verify a new mesh SSH connection:

```bash
ansible -i ../infra-inventory/hosts.yml test -m ansible.builtin.ping
```

Expected: `pong` through the inventory's NetBird name/automation SSH port.
Also request the node's existing public Nginx/Angie URL from outside the mesh;
it must give its usual response. Use the actual existing URL locally without
committing it, and do not substitute an unrelated public endpoint.

## State 3: recovery and firewall reload

On the test node:

```bash
sudo rm -f /etc/warp-native/watchdog.disabled
sudo systemctl start wg-quick@warp warp-native-watchdog.timer
sudo timeout 15 /usr/local/libexec/warp-native probe
sudo journalctl -u warp-native-watchdog.service -n 20 --no-pager
```

Expected: probe exit 0. Repeat state 1's two client requests: WARP/direct
results return. If intentionally testing more than three starts in ten minutes,
wait for the start limit to expire; do not disable the limit to hide a failure.

On this disposable node, if `nftables.service` was already in use, reload it,
then reload UFW and restart the CrowdSec bouncer through their usual service
paths. After **each** operation verify `inet warp_native`, both client
requests and a new mesh SSH connection. Keep WARP stopped for one reload and
repeat state 2 as well. Never enable a previously unused nftables.service just
to perform this test, and never issue a global ruleset flush. Reboot the test
node once and repeat both requests to verify service ordering and persistence.

To test watchdog recovery separately, leave its timer enabled, remove the
maintenance marker, stop only `wg-quick@warp` and wait for the next timer tick
(normally within 65 seconds). Expect the service to be restarted and the probe
to pass, with no further attempts during cooldown. This is separate from the
intentional failure test, which requires the watchdog to remain stopped.
