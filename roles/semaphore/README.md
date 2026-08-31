# Role: semaphore

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Deploys [Semaphore](https://semaphoreui.com/) (web UI for Ansible) on the
control node via Docker Compose, using the embedded SQLite database. Publishes the UI on
a local port for an existing reverse proxy to target; optionally joins an
external Docker network.

Requires Docker with the Compose v2 plugin on the target host.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `semaphore_image` | `semaphoreui/semaphore:v2.19.12` | Pinned container image |
| `semaphore_data_dir` | `/opt/semaphore` | Dir holding the compose file (data lives in named volumes) |
| `semaphore_bind` | `127.0.0.1:3000` | Host bind for the published port |
| `semaphore_internal_port` | `3000` | Container port |
| `semaphore_external_network` | `""` | Optional existing Docker network to join |
| `semaphore_admin_user` | `admin` | Admin login |
| `semaphore_admin_name` | `Admin` | Admin display name |
| `semaphore_admin_email` | `admin@localhost` | Admin email |
| `semaphore_db_dialect` | `sqlite` | Database backend (embedded; bolt deprecated) |
| `semaphore_admin_password` | _(required, OpenBao `infra/semaphore`)_ | Admin password |
| `semaphore_access_key_encryption` | _(required, OpenBao `infra/semaphore`)_ | base64 32-byte key; decrypts the Key Store — losing it makes Semaphore unable to read its own credentials |

Generate the encryption key once: `head -c 32 /dev/urandom | base64`.

## Dependencies

Collection `community.docker` (pinned in `requirements.yml`); Docker + Compose v2
on the host.

## Example

```yaml
- name: Deploy Semaphore on the control node
  hosts: control
  become: true
  roles:
    - role: semaphore
```

Then point your reverse proxy at `semaphore_bind` (or share a Docker network via
`semaphore_external_network`).

## Supported OS

Debian (bookworm, trixie), Ubuntu (jammy, noble).
