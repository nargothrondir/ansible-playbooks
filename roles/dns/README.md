# Role: dns

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Encrypted DNS for the host's **own** lookups — apt, ACME, the panel, mesh
names. Configures `systemd-resolved` with DNS-over-TLS to chosen upstreams, and
removes the interface-supplied nameservers that would otherwise override them.

It does **not** touch the VPN clients' DNS: xray resolves their traffic itself
over DoH, on a path that never reaches the system resolver.

### It installs the resolver, because the pipeline never did

On Debian 12+ `systemd-resolved` is a **separate package**, absent from a
minimal install. Every hand-built node here acquired it manually. The node
built entirely by the provisioning pipeline had no resolver at all — and
NetBird, finding none, took `/etc/resolv.conf` for itself as a plain file and
forwarded to whatever the provider image had configured, in **plaintext**:

```
un  systemd-resolved  <none>          ← package not installed
:53 → netbird only
/etc/resolv.conf (a plain file):  nameserver 100.64.0.0
```

So a node rebuilt through the pipeline loses encrypted DNS **silently** — it
does not fail, it just stops having it. The role therefore installs the
package, hands `resolv.conf` to the stub, and restarts NetBird so it
re-registers the mesh domain against the new resolver instead of owning the
file. On a host that already has all this, every one of those steps is a no-op.

The order is not arbitrary: upstreams are configured *before* resolved becomes
authoritative, because pointing `resolv.conf` at a resolver with no upstreams
breaks every lookup in the window between the two.

The replaced `resolv.conf` is copied to `/etc/resolv.conf.before-dns-role`
first. If the handover goes wrong, restoring that file and restarting NetBird
puts resolution back.

### The half that is easy to miss

`systemd-resolved` resolves per **scope**, and an interface's own servers beat
the global ones. Provider images ship `dns-nameservers` in the interface
config; `ifupdown` hands those to `resolvectl` (on Debian 13 `/sbin/resolvconf`
is a symlink to it), so the interface acquires its own resolvers and every
query goes there.

The global configuration then applies to nothing — while `resolvectl status`
still lists it and looks correct. Ask the link itself:

```bash
resolvectl dns ens3
# Link 2 (ens3): 203.0.113.53 198.51.100.53   ← its own servers, and they win
```

Do **not** try to read this off `resolvectl query`. Its `-- link: ens3`
annotation names the interface the *returned address* is reachable over, not
the scope that answered: a link with no DNS servers and no DNS scope at all
still stamps its name on every answer. That misreading cost an evening here,
and the role's own report used to repeat it.

So the role does two things, and the second is what makes the first real:
write the drop-in, and take the servers off the link.

### DoT, not DoH

`systemd-resolved` speaks DNS-over-TLS and **not** DNS-over-HTTPS. The two are
transports for the same job, not layers of protection — running both adds a
failure mode and no privacy.

- **DoT** uses port 853. Identifiable as DNS from the first packet and blocked
  with one filter rule, but native here, with no extra process.
- **DoH** uses 443 and is hard to block without breaking the web, at the cost
  of an always-running daemon that takes DNS down with it when it dies.

Prefer DoT; reach for DoH only on a host where 853 is actually filtered. That
is a per-host decision, not a fleet standard.

### Which resolvers, and why these

Two independent operators as primaries, each with both anycast addresses and
both address families; Google as fallback only. `systemd-resolved` tries the
list in order and stays on whichever answers, so this is a preference order and
not a pool.

**Cloudflare first** on latency — the widest anycast footprint, and every
lookup here sits on the critical path for apt, ACME and reaching the panel.
**Quad9 second** for independence: a different operator, a Swiss foundation,
DNSSEC-validating. **Google last**, because the most reliably reachable
resolver on the internet is the right thing to fall back to and the wrong thing
to prefer.

The IPv6 entries are not decoration. These nodes are dual-stack, and an
IPv4-only list turns an IPv4 incident the node would otherwise survive into a
total DNS outage.

Alternatives for a host where the defaults are filtered — Mullvad, dns0.eu,
AdGuard — are listed in `defaults/main.yml`. Set `dns_servers` in that host's
`host_vars`; do not change the default for the fleet. Note that a *filtering*
resolver answers NXDOMAIN for what it blocks, and a node needs registries,
mirrors and ACME endpoints to resolve rather than opinions about them.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `dns_servers` | Cloudflare, Quad9 (with hostnames) | Upstreams in preference order. The `#hostname` suffix lets the TLS certificate be checked by name. |
| `dns_fallback_servers` | `8.8.8.8#dns.google` | Used only when every server above is unreachable. |
| `dns_over_tls` | `true` | Strict DoT — no silent downgrade to plaintext. |
| `dns_dnssec` | `true` | Strict validation. Use `allow-downgrade` to prefer availability over authenticity. |
| `dns_search_domain` | `~.` | Makes the upstreams authoritative for domains no other scope claims. |
| `dns_manage_resolv_conf` | `true` | Install the resolver and point `/etc/resolv.conf` at its stub, restarting NetBird to re-register. |
| `dns_stub_resolv_conf` | `/run/systemd/resolve/stub-resolv.conf` | Where that symlink points. |
| `dns_allow_running_containers` | `false` | Run even though containers are up. They keep a stale resolver until restarted — see below. |
| `dns_strip_interface_nameservers` | `true` | Remove `dns-nameservers` from the interfaces file and clear the link's DNS. |
| `dns_interfaces_file` | `/etc/network/interfaces` | Where those lines live. |
| `dns_verify_name` | `deb.debian.org` | Name resolved after applying, to prove the resolver works. |

## What it verifies before reporting success

Configuration written is not configuration in effect, so the role checks
behaviour:

- `resolvectl` reports `+DNSOverTLS`;
- `dns_verify_name` resolves;
- this host's own `<name>.<netbird_dns_domain>` still resolves, when that
  variable is set — the mesh is how the panel reaches the node, and a global
  scope that swallowed the mesh domain leaves a node that serves traffic while
  becoming unmanageable.

The final debug line names the upstream the global scope settled on and whether
the default link kept any servers of its own, so a link that still wins is
visible rather than inferred.

## Three ways this can bite

**Running containers keep the old resolver.** Docker copies `/etc/resolv.conf`
into a container when the container is **created** and never revisits it.
Replacing the host's file leaves every running container pointing at the
resolver that was there before — which, once NetBird re-registers with
`systemd-resolved`, stops answering. Nothing fails during the play: the role
checks the host, and the host is correct. The containers simply stop resolving,
and on a Remnawave node the first thing that needs DNS is ACME renewal, up to
60 days later.

Measured on the lab node — the same ACME hook, either side of this role:

```
02:29:00  added TXT _acme-challenge...              ← before
04:40:43  ERROR ... Temporary failure in name resolution   ← after
```

So the role **stops** when it finds running containers. Restarting them
afterwards is the fix and gives each a fresh copy pointing at the stub; set
`dns_allow_running_containers=true` once that is arranged. Issue #153 tracks
making the stub reachable from the container network, which removes the need
for either.

**Strict DoT has no fallback.** If the chosen upstreams are unreachable,
resolution fails outright rather than degrading to plaintext — no apt, no ACME,
no resolving the panel by name. A typo in `dns_servers` takes the node off the
network by name.

**The interfaces file holds the static address.** The role removes only lines
matching `dns-nameservers` and takes a backup; it never rewrites the file. A
careless edit there leaves the host unreachable after the next reboot,
recoverable only through the provider's console.

The link's servers are cleared with `resolvectl revert`, which touches the
resolver and not the interface — bouncing the interface would drop the SSH
session running the play.

## Dependencies

None. Requires `systemd-resolved` to be the active resolver; the role asserts
this rather than assuming it.

## Example

```yaml
- hosts: fleet
  become: true
  roles:
    - role: dns
      vars:
        dns_servers:
          - "9.9.9.9#dns.quad9.net"
```

## Supported OS

Debian 12/13, Ubuntu 22.04/24.04 (`os_family == 'Debian'`).
