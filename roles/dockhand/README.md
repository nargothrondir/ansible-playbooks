# Role: dockhand

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Deploys [Dockhand](https://github.com/Finsys/dockhand) (Docker management UI) on
the control node via Docker Compose. It manages the **local** Docker host through
the mounted socket; remote hosts are managed by the Hawser agent (see the
`hawser` role). Data lives in a Docker named volume. The UI binds to loopback and
is meant to sit behind the reverse proxy (Netbird-only / IP-allowlisted).

> On first launch authentication is **disabled** — enable it immediately in
> **Settings → Authentication** and create the admin user.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `dockhand_image` | `fnsys/dockhand:v1.0.43` | Pinned image |
| `dockhand_bind` | `127.0.0.1:3040` | Host bind for the UI (behind the proxy) |
| `dockhand_data_dir` | `/opt/dockhand` | Dir holding the compose file (data in a named volume) |
| `dockhand_puid` / `dockhand_pgid` | `1000` | Container user/group ids |
| `dockhand_encryption_key` | _(required, vaulted)_ | Base64 AES-256 key (44 chars) for credential encryption |

`dockhand_encryption_key` must be a base64-encoded 32-byte key
(`openssl rand -base64 32`), supplied via ansible-vault.

## Dependencies

`community.docker` (for `docker_compose_v2`). Docker must be installed on the host.

## Example

```yaml
- name: Deploy Dockhand
  hosts: control
  become: true
  roles:
    - role: dockhand
```

## Supported OS

Debian (bookworm, trixie), Ubuntu (jammy, noble).
