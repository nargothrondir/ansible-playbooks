# Role: upgrade

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Updates the apt cache, upgrades installed packages, removes obsolete ones,
and reboots the host only when the running kernel is no longer the newest one
installed. Equivalent to:

```bash
apt update && apt full-upgrade -y && apt autoremove --purge -y
```

The upgrade is idempotent: if nothing needs upgrading, no changes are made and
no reboot is triggered.

**Why a host would hold packages.** The control plane cannot safely update the
things it is running on. Semaphore executes `ansible-playbook` inside a
container on the panel, and `docker-ce`'s postinst restarts the daemon — which
kills that container and the play with it. The task neither fails nor
finishes; the run simply stops existing, with no `PLAY RECAP` and no report.
Listing those packages in `upgrade_hold_packages` marks them `hold` before the
upgrade runs.

A hold is a promise to update the package by hand, so the role refuses to let
that promise go quiet: apt still *lists* a held package as upgradable, it just
will not touch it, and the role announces any held package with an update
waiting on every run. Without that, the host would sit on an unpatched package
indefinitely while every run reported success.

**How the reboot decision is made.** `/var/run/reboot-required` is an *Ubuntu*
convention: the hook that creates it ships in `update-notifier-common`, which
minimal Debian neither installs nor pulls in. Relying on that marker alone made
the check a permanent no-op on Debian hosts — a run could upgrade the kernel,
glibc and systemd and still skip the reboot. The role therefore installs
`needrestart` and reads `NEEDRESTART-KSTA` from its batch output (`2` =
ABI-compatible upgrade pending, `3` = version upgrade pending); the marker is
still honoured where it does exist. `needrestart` is pinned to list-only mode
so its apt hook can never prompt in the middle of an Ansible run.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `upgrade_apt_type` | `dist` | apt strategy (`dist` = full-upgrade; `safe` = no removals) |
| `upgrade_autoremove` | `true` | Remove no-longer-required packages |
| `upgrade_autoremove_purge` | `true` | Purge config files when autoremoving |
| `upgrade_cache_valid_time` | `3600` | Seconds the apt cache is considered fresh |
| `upgrade_hold_packages` | `[]` | Packages this host must never upgrade unattended |
| `upgrade_reboot` | `true` | Reboot automatically when required |
| `upgrade_reboot_timeout` | `600` | Seconds to wait for the host after reboot |

## Dependencies

None. Requires privilege escalation (`become: true`) on the target host.

## Example

```yaml
- name: Update and upgrade servers
  hosts: new_vps
  become: true
  gather_facts: true
  vars:
    ansible_user: ansible
    ansible_ssh_private_key_file: "~/.ssh/ansible_ed25519"
  roles:
    - role: upgrade
```

## Supported OS

Debian (bookworm, trixie), Ubuntu (jammy, noble).
