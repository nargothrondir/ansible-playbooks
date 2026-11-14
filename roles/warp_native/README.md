# Role: warp_native

English · [Русский](README.ru.md)

## Description

IPv4-only Cloudflare WARP on a separate host WireGuard interface `warp`.
Only Xray outbounds explicitly bound to `warp` and marked **51888** use it.
The host's main routes, NetBird `wt0`, UFW, CrowdSec and resolver are preserved.

The role owns `inet warp_native` (output hook, priority -10). Its drop rule is
`meta mark 51888 oifname != "warp" counter drop` and survives interface stops.
It also owns IPv4 policy priority 10088 and table 51888: a marked lookup has a default
route through `warp` (metric 10) and a persistent unreachable default (42760).
This closes the gap while another firewall reloads its rules. `Table = off`
prevents wg-quick from changing the main routes; there is no `DNS =` setting.

No additional firewall service is enabled. Drop-ins append reconciliation to
the existing `nftables.service` start/reload/stop, preserving its vendor
commands. UFW edits its own iptables chains; the CrowdSec bouncer owns separate
tables. Arbitrary manual changes to these policy rules are outside this
guarantee. Never remove the guard while a profile still uses `warp-out`.

Preflight rejects existing WARP installations without this role's ownership
marker, occupied marks/priorities/tables, masked mark conflicts, and unknown
dynamic mark writers that might produce 51888. Review a rejection; do not
rename an unrelated table or blindly adopt a shell installation. It checks
both nftables and iptables-legacy state, IPv4/IPv6 policy rules and WG marks.

wgcf **2.3.1** is pinned together with upstream SHA-256 hashes for amd64 and
arm64 in `vars/main.yml`. A root-only binary lives in `/usr/local/lib/warp-native`.
Device registration runs once with umask 0077. The account and reusable profile
remain under `/var/lib/warp-native` (0700; files 0600); `/etc/wireguard/warp.conf`
is 0600. Credentials are processed only on the node, with `no_log` and no diff.
The endpoint from wgcf is resolved strictly to IPv4 and cached on first rendering; an explicit
`warp_native_endpoint` can pin a numeric IPv4 endpoint instead.
Changing that variable invalidates the cache. Delete the role's
`/var/lib/warp-native/endpoint.json` before reapplying to force a DNS refresh.

## Variables

| Variable | Default | Meaning |
|---|---|---|
| `warp_native_state` | `present` | `present` or `absent` |
| `warp_native_purge_account` | `false` | Also delete saved identity during removal |
| `warp_native_watchdog_enabled` | `true` | Enable the systemd watchdog timer |
| `warp_native_watchdog_interval` | `60` | Seconds between completed checks; minimum 30 |
| `warp_native_watchdog_cooldown` | `180` | Minimum seconds between restart attempts; minimum 120 |
| `warp_native_probe_timeout` | `10` | Probe timeout in seconds, 2–30 |
| `warp_native_endpoint` | `""` | Use generated endpoint; optional IPv4 or hostname with port |
| `warp_native_mtu` | `1280` | Interface MTU, 1280–1420 |
| `warp_native_keepalive` | `25` | WireGuard keepalive seconds, 0–65535 |

Names, mark and table are deliberately fixed. The watchdog performs a marked,
interface-bound HTTPS request to Cloudflare's trace endpoint, verifies TLS and
accepts only HTTP 200 with `warp=on` or `warp=plus`. The complete check has a
deadline. Old handshakes do not trigger recovery. Failed attempts also consume
the cooldown; wg-quick additionally limits starts to three per ten minutes.

## Dependencies

Debian packages: `wireguard-tools`, `nftables`, `iproute2`, `ca-certificates`,
`python3`; systemd and a kernel supporting WireGuard/nftables are required.
No Galaxy role, warp-cli, SOCKS daemon, DNS rewrite or external installer.
The invoking play/role sets `become: true`. Normal and check-mode runs require
root to inspect firewall state and `python3-apt` for APT check mode. First-install check mode does not register an
account or generate a profile; runtime checks require a real installation.

## Example

From the repository root, using the separate private inventory and its `test`
host from the example layout:

```bash
ansible-playbook -i ../infra-inventory/hosts.yml playbooks/warp-native.yml \
  -e warp_native_target=test --check --diff
ansible-playbook -i ../infra-inventory/hosts.yml playbooks/warp-native.yml \
  -e warp_native_target=test
ansible-playbook -i ../infra-inventory/hosts.yml playbooks/warp-native.yml \
  -e warp_native_target=test
```

Expected: preflight/check succeeds; the installation succeeds; the second real
run reports `changed=0`. These commands are operator instructions, not a record
of a deployment. Replace `test` with one explicitly chosen disposable node.
The playbook refuses group patterns and is not imported into provisioning.

```bash
ansible -i ../infra-inventory/hosts.yml test -b -m ansible.builtin.command \
  -a 'systemctl status wg-quick@warp warp-native-guard warp-native-watchdog.timer --no-pager'
ansible -i ../infra-inventory/hosts.yml test -b -m ansible.builtin.command \
  -a 'nft list table inet warp_native'
ansible -i ../infra-inventory/hosts.yml test -b -m ansible.builtin.command \
  -a 'timeout 15 /usr/local/libexec/warp-native probe'
```

Expected: services active, one marked output drop rule, probe exit code zero.
The probe prints no credentials or source address. `wg show warp` is safe;
`wg showconf`, `wg show ... dump` and account/profile contents contain secrets.

## Xray and acceptance tests

See [TESTING.md](TESTING.md) for the ready JSON fragment, DNS explanation,
container capability checks and exact healthy / failed / recovered commands.
The repository already manages profile creation; its optional
`profile_use_warp` template now uses `ForceIPv4` and mark 51888. This changes
future generated profiles only. No panel API or live profile is changed by
this role. `DIRECT` remains the default outbound and has no mark.

The inspected `docker-stacks/remnanode/docker-compose.yml` uses host networking
and `cap_add: [NET_ADMIN]`, so the container can see host `warp` and has the
capability required for `SO_MARK`. Actual Xray process capabilities still need
verification on the chosen node. No Compose networking/capabilities are altered.

## Maintenance and rollback

On the selected test node, maintenance can persist across reboots:

```bash
sudo touch /etc/warp-native/watchdog.disabled
sudo systemctl stop warp-native-watchdog.timer warp-native-watchdog.service
sudo systemctl stop wg-quick@warp
```

Expected: the interface stops, but the nft drop and unreachable route remain.
Resume with `sudo rm -f /etc/warp-native/watchdog.disabled`, then
`sudo systemctl start wg-quick@warp warp-native-watchdog.timer`. Expected: a
successful trace probe. Setting `warp_native_watchdog_enabled: false` also
disables the timer through Ansible; it does not request interface removal.

Before uninstalling, remove `warp-out` and its routing references from the
test profile and verify that it no longer selects WARP traffic. Then:

```bash
ansible-playbook -i ../infra-inventory/hosts.yml playbooks/warp-native.yml \
  -e warp_native_target=test -e warp_native_state=absent
```

Expected: only this role's services, drop-ins, interface config, policy
rule/routes, nft table and executables disappear. The device identity is kept
for reinstallation; add `-e warp_native_purge_account=true` to that removal
command to delete it too. No shared packages, UFW/CrowdSec files, resolver or
other WireGuard interfaces are removed. Removing the role from a play alone
does not uninstall host state.

## Supported OS

Debian 12 (bookworm) and 13 (trixie), amd64 / arm64, systemd.

## References

[warp-native installer](https://github.com/distillium/warp-native),
[wgcf](https://github.com/ViRb3/wgcf/releases/tag/v2.3.1),
[wgcf checksums](https://github.com/ViRb3/wgcf/releases/download/v2.3.1/checksums.txt),
[Ansible reference role](https://github.com/TheMelbine/ansible-role-warp-native).
The implementation does not copy the installer's DNS changes, cron watchdog,
package removal or unconditional interface resets.
