# ufw

**English** | [Русский](README.ru.md)

## Description

Host firewall for fleet nodes: deny incoming by default, allow a short list of
public TCP ports, and open service ports **only on the NetBird mesh interface**.

The mesh rule is bound to the interface, not to a peer IP: mesh IPs are owned
by NetBird's IPAM and regenerate on the self-host migration (#6), so pinning
them into host rules would go stale silently. *Who* inside the mesh may connect
is enforced by NetBird Access Control policies; the host firewall only enforces
*"mesh only"* (defense in depth, see issue #49).

Rules are laid down before the firewall is enabled, so enabling over SSH is
safe. Docker note: published container ports bypass ufw — the remnanode stack
uses `network_mode: host`, so this does not apply to fleet nodes.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ufw_public_tcp` | `[{port: 22, comment: SSH}, {port: 443, comment: HTTPS}]` | TCP ports allowed from anywhere; `comment` appears in `ufw status` |
| `ufw_mesh_tcp` | `[{port: 2222, …}, {port: automation_ssh_port, …}, {port: 22022, …}]` | TCP ports allowed only from the mesh interface. 22022 is NB-SSH's endpoint — NetBird does not open it itself |
| `ufw_mesh_interface` | `wt0` | NetBird (WireGuard) interface name |

## Dependencies

None (`community.general` collection for the `ufw` module).

## Example

```yaml
- hosts: fleet
  become: true
  roles:
    - ufw
```

## Supported OS

Debian 12/13, Ubuntu 24.04.
