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

## Trusting the fleet SSH CA

Optional second job, off unless `ssh_hardening_ca_public_key` is given a value:
install a certificate authority's public key and tell sshd to accept user
certificates signed by it.

**It adds a credential and removes none.** `authorized_keys` is not touched by
this role, so the existing key remains the way in and a certificate that fails
to verify is simply not a second way. That is deliberate — a trust anchor
installed wrongly should cost a failed experiment, not a locked door. Removing
it again needs no playbook: delete `/etc/ssh/sshd_config.d/20-ansible-ca.conf`
and reload sshd.

The key is written before the drop-in that names it, because
`TrustedUserCAKeys` pointing at a missing file makes sshd log an error at every
authentication attempt. Both tasks share one `when`, so a host never ends up
holding half of the arrangement.

`AuthorizedPrincipalsFile` is deliberately not configured. Without it sshd
accepts a certificate whose principal list contains the target username, which
is exactly the rule the fleet CA's signing role already enforces at issue time.

Two checks run after the reload, and they answer different questions.
`sshd -t` says the merged configuration parses; `sshd -T` says what it merged.
A drop-in that was never included — no `Include` line in the provider's
`sshd_config` — passes the first and is missing from the second. Without the
second check, certificate trust would look installed and do nothing, and the
discovery would be a login that quietly fell back to the key.

A green run does **not** prove that a certificate login works. It proves sshd
is serving the directive. The credential half is proven separately by
[playbooks/openbao-ssh-sign.yml](../../playbooks/openbao-ssh-sign.yml); putting
the two together is a login, performed by hand once per host.

The key itself comes from OpenBao at `infra/ssh_ca`, read on the controller and
handed to the node — nodes cannot reach OpenBao, whose API is on a Docker
network the panel owns rather than on the mesh. Two callers do that:
[playbooks/provision-node.yml](../../playbooks/provision-node.yml) for a node
being built, so it is a normal fleet member from the start, and
[playbooks/ssh-ca-trust.yml](../../playbooks/ssh-ca-trust.yml) for one that
already exists.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ssh_hardening_mesh_port` | `automation_ssh_port` (2200) | Additional sshd port for automation over the mesh; shared with the ufw role via group_vars/all |
| `ssh_hardening_public_port` | `22` | The host's canonical public sshd port kept in the drop-in; override on hosts deliberately off 22 |
| `ssh_hardening_ca_public_key` | `""` | Fleet CA public key (`infra/ssh_ca` in OpenBao). Empty leaves sshd's credentials untouched; a value installs certificate trust alongside `authorized_keys` |
| `ssh_hardening_ca_path` | `/etc/ssh/trusted-user-ca.pub` | Where that key is written. Public by construction, world-readable |

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
