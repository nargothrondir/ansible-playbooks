# Role: crowdsec

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Installs [CrowdSec](https://crowdsec.net) and the nftables firewall bouncer, and
protects the host against **SSH** attacks with **progressive (exponential)**
bans enforced locally.

Design choices (see issue #31):

- **SSH-only.** Only the `crowdsecurity/sshd` collection is ingested. The
  reality/camouflage 443 access log is deliberately **not** watched, so nothing
  can ever drive a ban on 443 — a ban there would be a behavioural fingerprint
  no plain website exhibits.
- **Progressive bans.** The ban duration doubles per prior decision for the same
  IP (`1h → 2h → 4h …`), capped at one week. Encoded as a `duration_expr` in
  `profiles.yaml` using `GetDecisionsCount`.
- **Anti-lockout whitelist.** The Netbird mesh range (and any admin IPs) are
  whitelisted so the panel↔node LAPI path and your own access can never produce
  a ban.
- **Central LAPI wiring is present but inactive by default.** With
  `crowdsec_central_lapi_enabled: false` the node runs standalone (its own local
  LAPI). Flip it on later to report to the panel's LAPI over the mesh, without
  re-architecting.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `crowdsec_collections` | `[crowdsecurity/sshd]` | Collections to install. SSH only by design. |
| `crowdsec_ban_base_hours` | `1` | First-offence ban length, in hours. |
| `crowdsec_ban_cap` | `168h` | Ceiling for the exponential ban (one week). |
| `crowdsec_ban_cap_threshold` | `7` | Prior-decision count above which the cap applies. |
| `crowdsec_whitelist_cidrs` | `[100.64.0.0/10]` | CIDRs CrowdSec must never act on (mesh + admin). |
| `crowdsec_central_lapi_enabled` | `false` | Report to the panel's central LAPI (fleet-wide) instead of the local one. |
| `crowdsec_central_lapi_url` | `""` | Central LAPI URL over the mesh (when enabled). |
| `crowdsec_central_lapi_login` | `{{ inventory_hostname }}` | Machine login registered on the panel (when enabled). |
| `crowdsec_central_lapi_password` | `""` | Machine password — put it in OpenBao when this is activated. |

### Why the bouncer is registered explicitly

The `crowdsec-firewall-bouncer-nftables` package registers itself in its
postinst by calling `cscli bouncers add`, which needs a running LAPI — and the
LAPI *is* the agent. Both packages install in one apt transaction, so on a fresh
machine the agent is not up yet when the bouncer is configured. The registration
fails quietly, the shipped placeholder stays in the config, and the service then
dies on every start with:

```
level=fatal msg="process terminated with error: API error: access forbidden"
```

with `cscli bouncers list` empty. Seen on the first fresh-install run of the
provisioning pipeline.

The role had always registered the bouncer itself — but *after* trying to start
it. The failed start aborted the play before the registration ran, so the fix
was ordering, not a missing step.

So the role starts the agent alone first, then registers the bouncer itself and
writes the key, and only then starts the bouncer. The guard is the key's
*length* rather than a match against the placeholder string, which also makes a
half-configured machine repair itself on the next run: a stale registration
under the same name is dropped and remade, because `cscli` cannot reveal an
existing key.

## Dependencies

None (role-level). Expects `common` to have run first in the pipeline (baseline
packages incl. `python3-debian` for `deb822_repository`); the role also installs
those prerequisites itself for standalone/DR runs.

Enabling `crowdsec_central_lapi_enabled` additionally requires the **panel side**:
`cscli machines add <login>` for the agent and a bouncer API key issued on the
panel.

## Example

```yaml
- hosts: nodes
  become: true
  roles:
    - role: crowdsec
      vars:
        crowdsec_whitelist_cidrs:
          - "100.64.0.0/10"     # mesh
          - "203.0.113.5/32"    # admin
```

## Supported OS

Debian 12/13, Ubuntu 22.04/24.04 (`os_family == 'Debian'`).
