# Role: debian_release

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Moves a Debian host to a newer major release, following the procedure in
Debian's release notes, one release at a time. Does nothing unless
`debian_release_target` is set, and nothing on a host already at or past it.

Debian supports upgrading only from the release immediately before the new one,
so a host two releases behind passes through the one in between, with a reboot
and every check repeated at each step. A failure stops the host on a consistent
release rather than halfway through a transition.

### Order of one step

1. **Update the current release fully.** The release notes assume the latest
   point release. This also pulls in the fixes some steps depend on.
2. **Check this step's preconditions.** Package minimums from the release
   table, compared with `dpkg --compare-versions`.
3. **Pin network interface names.** One `.link` file per physical interface,
   written before anything changes, and the initramfs rebuilt so early boot
   agrees.
4. **Switch the sources** through the `apt_sources` role with the new codename.
5. **Minimal upgrade:** `apt-get upgrade`, which installs nothing new and
   removes nothing.
6. **Simulate the full upgrade** and stop if it would remove any package.
7. **Full upgrade:** `apt-get dist-upgrade`.
8. **Reboot**, re-read facts, and confirm the new version.

Before the first step the role also refuses to start when `dpkg --audit`
reports unfinished packages, when any package is held, or when `/`, `/usr` or
`/var` has less than `debian_release_min_free_mb` free.

### Why each safeguard is there

**Two stages, as Debian prescribes.** The release notes warn that a direct full
upgrade "might remove large numbers of packages that you will want to keep". On
a freshly built node the difference is small; this role is also meant for nodes
already carrying the full stack, where it is not.

**The simulation.** `apt-get -y` aborts on its own only when an *essential*
package would be removed. Anything else it removes without asking. The minimal
stage reduces removals; the simulation refuses the remainder and prints the
list.

**Async with a generous limit.** An upgrade supervised over SSH must survive the
connection dropping — sshd itself restarts during it, and the trixie release
notes (5.1.1) describe bookworm's OpenSSH stranding a remote system when an
upgrade is interrupted. Ansible's async wrapper forks twice, calls `setsid` and
detaches from the session, so the transaction continues if the connection goes.
The limit is generous for the opposite reason: when it expires the wrapper sends
`SIGKILL` to the whole process group, and a killed dpkg breaks a system far more
thoroughly than a slow mirror.

**Interface pins before the upgrade, not after.** A new release can name an
interface differently (trixie notes, 5.1.17), and an interface that no longer
matches `/etc/network/interfaces` is a host with no network after the reboot —
on a VPS, one nothing can reach. Written first, the pins make an interrupted run
safe at any point: after the full upgrade `/etc/debian_version` already names
the new release, so a re-run would skip the step and never reach a pin placed
later. Physical interfaces are the ones whose facts carry `module`; veth,
bridges, WireGuard and loopback do not. Debian's udev initramfs hook copies
every `.link` from `/etc/systemd/network` into the image, which is why the role
rebuilds it after writing a pin.

**A space floor instead of apt's estimate.** apt prints its estimate in a format
that changed between apt 2.6 and apt 3, and a check that quietly stops parsing
on the next release is worse than a coarse one. apt still runs its own checks.

### Adding a release

`_debian_release_known` in `vars/main.yml` lists every release the role may move
a host to. Adding an entry is the statement that the release's notes were read:
each release has its own chapter of known issues, and anything in it that could
strand a remote host belongs in the entry as a precondition, or as a new step in
`tasks/step.yml`, before it is committed. A target the table does not know is
refused before anything runs.

### After the move, on a node that already runs things

Third-party repositories are not this role's: `roles/docker` and `roles/xanmod`
write their suite from `ansible_facts['distribution_release']`, so they keep the
old codename until those roles run again. In `provision-node.yml` this role runs
before either is installed, so nothing is affected there. On an existing node,
re-apply them after the move.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `debian_release_target` | `""` | Major version to end on, as a string (`"13"`). Empty: do nothing |
| `debian_release_min_free_mb` | `2048` | Minimum free MiB on `/`, and on `/usr` and `/var` when separate |
| `debian_release_async_timeout` | `3600` | Upper bound in seconds for each apt transaction |
| `debian_release_async_poll` | `15` | Seconds between checks on a running transaction |
| `debian_release_reboot_timeout` | `900` | Seconds to wait for the host after the reboot |
| `debian_release_pin_interface_names` | `true` | Pin physical interface names with `.link` files first |
| `debian_release_link_dir` | `/etc/systemd/network` | Where the pin files go |

## Dependencies

Includes `apt_sources` at run time to switch the Debian sources. No `meta`
dependency. Requires privilege escalation (`become: true`).

## Example

```yaml
- name: Move a node to Debian 13
  hosts: new_vps
  become: true
  gather_facts: true
  vars:
    debian_release_target: "13"
  roles:
    - apt_sources
    - upgrade
    - debian_release
```

## Supported OS

Debian bookworm → trixie. Further releases once they are added to
`_debian_release_known`.
