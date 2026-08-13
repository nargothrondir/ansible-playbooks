# Role: hawser

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Deploys the [Hawser](https://github.com/Finsys/hawser) agent (for
[Dockhand](https://github.com/Finsys/dockhand)) on a remote Docker host in
**edge mode** — the agent connects outbound to Dockhand over WebSocket, so no
inbound port/forwarding is needed (good for VPS/NAT and censored hosts).

Each host is a separate Dockhand environment with its **own token**.

The token is rendered into the compose file, which is written `0600` (root-only)
by a task running with `no_log`, so it is neither world-readable nor logged.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `hawser_image` | `ghcr.io/finsys/hawser:0.2.46` | Pinned agent image |
| `hawser_dir` | `/opt/hawser` | Dir holding the agent compose file |
| `hawser_stacks_dir` | `/opt/hawser-stacks` | `STACKS_DIR` for Hawser-managed stacks |
| `hawser_request_timeout` | `180` | Agent `REQUEST_TIMEOUT` (s); upstream default 30 s cancels long cold deploys |
| `hawser_dockhand_url` | _(required)_ | Dockhand edge endpoint (`wss://…/api/hawser/connect`), set in `group_vars/all` |
| `hawser_token` | _(required, vaulted)_ | Per-host agent token (e.g. from a `hawser_host_tokens` mapping in `group_vars/managed/vault.yml`) |

## Dependencies

`community.docker` (for `docker_compose_v2`). Docker must be installed on the host.

## Example

```yaml
- name: Deploy Hawser
  hosts: managed
  become: true
  tasks:
    - ansible.builtin.include_role:
        name: hawser
      when: hawser_token | default('') | length > 0
```

## Supported OS

Debian (bookworm, trixie), Ubuntu (jammy, noble).
