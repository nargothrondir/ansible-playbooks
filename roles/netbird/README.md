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

### SSH access

The NetBird SSH server is the fleet's break-glass: it arrives over the mesh, so
a CrowdSec ban, a bad ufw rule or a broken sshd does not close it. Root login
through it is a separate switch, `netbird_ssh_root` — off in the role, on in
`provision-node.yml` — because escalating from the automation user depends on
sudo, PAM and a writable disk, which are what tends to be broken when the
break-glass is needed.

Who may log in as whom is decided by the server in this order:

1. **The policy.** A NetBird SSH policy must list the user's group as a source
   and map it to the local user. *Limited Access* maps the users it names;
   *Full Access* maps every local user, **root included**. No mapping: denied.
2. **`netbird_ssh_root`.** Refuses root when false, whatever the policy says.

With root enabled, the policy alone decides who gets it. Keep the SSH policy on
*Limited Access*, with `root` listed for the operators' group only.

The role reads the settings the agent runs with on every run and re-applies
them when they differ. NetBird applies SSH flags only in `netbird up`, and `up`
on a connected peer changes nothing, so re-applying is `netbird down && netbird
up`: the node is off the mesh, and unreachable from the panel, for a few
seconds. It runs detached, so it completes even when Ansible itself connects
over the mesh. The settings are read without reading the configuration file
into the run — that file holds the peer's WireGuard private key.

Set `netbird_management_url` to point the agent at a self-hosted management
server (issue #6); left empty it uses the NetBird cloud.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `netbird_setup_key` | `""` | Reusable setup key (secret) — provide via vault |
| `netbird_management_url` | `""` | Self-hosted management URL; empty = NetBird cloud |
| `netbird_ssh_server` | `true` | Run the NetBird SSH server (`--allow-server-ssh`) — the fleet break-glass (`--disable-ssh-auth` is never passed). Needs port 22022 open on the mesh interface, see `roles/ufw` |
| `netbird_ssh_root` | `false` | Allow root login through it (`--enable-ssh-root`). Requires `netbird_ssh_server`; the policy still decides who, see [SSH access](#ssh-access) |
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
