# ssh_hardening

**English** | [Русский](README.ru.md)

## Description

SSH hardening for fleet hosts. Current scope (step 1 of issue #30): open an
**additional sshd port for key-based automation over the NetBird mesh**.

Why a second port: on peers with NB-SSH enabled, NetBird intercepts mesh
traffic to port 22 (redirecting it to its embedded JWT/SSO server for the
dashboard's in-browser break-glass SSH), so classic key auth never reaches
sshd there. Ansible therefore gets its own door — a port the interception does
not touch. The [ufw role](../ufw/README.md) opens it on the mesh interface
only; it is never exposed publicly.

The drop-in lists `Port 22` explicitly as well: the first `Port` directive
replaces the implicit default, while multiple `Port` lines accumulate. The
merged config is validated (`sshd -t`) before the reload handler fires.

Future steps of #30 (disable password auth, root login, crypto hardening) will
extend this role.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ssh_hardening_mesh_port` | `automation_ssh_port` (2200) | Additional sshd port for automation over the mesh; shared with the ufw role via group_vars/all |
| `ssh_hardening_public_port` | `22` | The host's canonical public sshd port kept in the drop-in; override on hosts deliberately off 22 |

## Dependencies

None. Pair with the `ufw` role (`ufw_mesh_tcp`) to keep the port mesh-only.

## Example

```yaml
- hosts: fleet
  become: true
  roles:
    - ssh_hardening
```

## Supported OS

Debian 12/13, Ubuntu 24.04.
