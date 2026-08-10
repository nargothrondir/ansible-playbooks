# Role: dns

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Encrypted DNS for the host's **own** lookups — apt, ACME, the panel, mesh
names. Configures `systemd-resolved` with DNS-over-TLS to chosen upstreams, and
removes the interface-supplied nameservers that would otherwise override them.

It does **not** touch the VPN clients' DNS: xray resolves their traffic itself
over DoH, on a path that never reaches the system resolver.

### The half that is easy to miss

`systemd-resolved` resolves per **scope**, and an interface's own servers beat
the global ones. Provider images ship `dns-nameservers` in the interface
config; `ifupdown` hands those to `resolvectl` (on Debian 13 `/sbin/resolvconf`
is a symlink to it), so the interface acquires its own resolvers and every
query goes there.

The global configuration then applies to nothing — while `resolvectl status`
still lists it and looks correct. The only way to see it is to ask which scope
answered:

```bash
resolvectl query --cache=no github.com
# github.com: 140.82.121.3   -- link: ens3      ← the interface won
```

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

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `dns_servers` | Cloudflare, Quad9 (with hostnames) | Upstreams in preference order. The `#hostname` suffix lets the TLS certificate be checked by name. |
| `dns_fallback_servers` | `8.8.8.8#dns.google` | Used only when every server above is unreachable. |
| `dns_over_tls` | `true` | Strict DoT — no silent downgrade to plaintext. |
| `dns_dnssec` | `true` | Strict validation. Use `allow-downgrade` to prefer availability over authenticity. |
| `dns_search_domain` | `~.` | Makes the upstreams authoritative for domains no other scope claims. |
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

The final debug line names which scope answered, so a link that still wins is
visible rather than inferred.

## Two ways this can bite

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
