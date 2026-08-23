# Role: beszel_agent

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Installs the [Beszel](https://beszel.dev) monitoring agent as a **binary +
systemd service** (not Docker), adopting the layout of Beszel's own installer
(user `beszel`, binary in `/opt/beszel-agent`, sandboxed unit).

- **WebSocket connection:** the agent dials the hub (`HUB_URL` + a per-node
  `TOKEN`), so it opens **no inbound port** — private-by-default friendly.
- **Auto-registration via the hub API:** the role registers each node in the hub
  (PocketBase) and issues its **per-node token** through the API — and also
  **fetches the hub's public key** and the owner user automatically. The only
  thing set by hand is the hub superuser credentials (in vault). Idempotent (an
  existing system's token is read back). Disable with
  `beszel_agent_register: false` to provide the token/key yourself.
- **Self-update aware:** the binary is installed only when absent (a `creates`
  guard). Beszel updates itself afterwards, so the role never re-pins or fights
  it — the pinned version is just the bootstrap for a bare node.
- **Container stats:** the agent user is added to the `docker` group to read
  `/var/run/docker.sock`.
- The token is rendered into the unit, which is written `0600` (root-only) and
  the task runs with `no_log`, so it is not world-readable or logged.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `beszel_agent_version` | `0.18.7` | Bootstrap binary version (install-if-absent; Beszel self-updates after). |
| `beszel_agent_arch` | `amd64` | Release architecture. |
| `beszel_agent_hub_url` | `""` | **Required** — hub URL (WebSocket + registration API). Set it in the inventory; not defaulted here so no real hostname ships with the repo. |
| `beszel_agent_key` | `""` | Hub public key. Auto-fetched during registration; set only if `register` is off. |
| `beszel_agent_token` | `""` | Per-node token. Left empty — filled by auto-registration (or set it yourself if disabled). |
| `beszel_agent_register` | `true` | Register the node in the hub via the API; fetches key/owner and issues the token. |
| `beszel_agent_admin_email` | `vault_beszel_admin_email` | Hub PocketBase **superuser** email (registration). |
| `beszel_agent_admin_password` | `""` | Hub superuser password — from OpenBao `infra/beszel`, supplied by the playbook. |
| `beszel_agent_owner_email` | `""` | Dashboard owner of the systems; empty = the sole/first user. |
| `beszel_agent_system_name` | `{{ inventory_hostname }}` | System name in the hub. |
| `beszel_agent_system_host` | `{{ inventory_hostname }}` | Display host (nominal for WebSocket). |
| `beszel_agent_docker_group` | `true` | Add the agent user to `docker` for container stats. |
| `beszel_agent_extra_filesystems` | `""` | `EXTRA_FILESYSTEMS` (extra disks to monitor). |
| `beszel_agent_port` | `45876` | `PORT` (SSH-mode listen; unused while `HUB_URL` is set). |

## Dependencies

None (role-level). Docker must be present if `beszel_agent_docker_group` is
`true`. Auto-registration needs only the hub's **superuser** credentials (in
vault); the hub key and owner user are fetched from the PocketBase API.

## Example

```yaml
# group_vars/*/vault.yml   (the only thing set by hand)
vault_beszel_admin_email: "admin@example.com"
vault_beszel_admin_password: "…"
```

```yaml
- hosts: fleet:!panel
  become: true
  roles:
    - beszel_agent
```

## Supported OS

Debian 12/13, Ubuntu 22.04/24.04 (`os_family == 'Debian'`).
