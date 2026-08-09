# Role: netbird

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Installs the [NetBird](https://netbird.io/) agent from the official APT
repository (signing key → `/etc/apt/keyrings/netbird.asc`, deb822 source →
`/etc/apt/sources.list.d/netbird.sources`), enables the service, and joins the
mesh non-interactively with a **setup key**.

The join is idempotent (fetch-then-guard): `netbird status` is read first and
`netbird up` runs only when the host is not already connected — so the role is
safe to run against hosts that already joined (e.g. the existing fleet).

Set `netbird_management_url` to point the agent at a self-hosted management
server (issue #6); left empty it uses the NetBird cloud.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `netbird_setup_key` | `""` | Reusable setup key (secret) — provide via vault |
| `netbird_management_url` | `""` | Self-hosted management URL; empty = NetBird cloud |
| `netbird_ssh_server` | `true` | Pass `--allow-server-ssh` on join — the fleet break-glass (root login deliberately not offered; `--disable-ssh-auth` never passed). Needs port 22022 open on the mesh interface, see `roles/ufw`. Applied only when the peer actually joins |
| `netbird_apt_arch` | `amd64` | APT repository architecture |

The setup key is handled with `no_log: true`.

## Dependencies

None.

## Example

```yaml
- hosts: managed
  become: true
  roles:
    - role: netbird
```

## Supported OS

Debian 12/13, Ubuntu 22.04/24.04 (`os_family == 'Debian'`).
