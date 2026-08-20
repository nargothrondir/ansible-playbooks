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

## Retiring passwords

The role's third optional job, off unless `ssh_hardening_disable_password_auth`
is true. It writes `/etc/ssh/sshd_config.d/30-ansible-auth.conf` with three
directives and no more.

`KbdInteractiveAuthentication no` is not redundant beside
`PasswordAuthentication no`. With only the latter, PAM still accepts a password
through keyboard-interactive, and the host reports itself hardened while
remaining exactly as reachable as before. Both lines, always.

`PermitRootLogin` defaults to `prohibit-password`, not `no`. Root stays
reachable **by key** — the provider's admin key, which is the break-glass that
depends on neither OpenBao nor NetBird nor this role. Closing that door as well
is a separate decision, and it should be made knowing that the provider's
console becomes the only way back.

**This is the one setting here that can end with nobody able to reach the
host**, so it defaults to off and is rolled out per host. Two things guard it,
and they are guards of different kinds:

- The automation user needs no check. The role is running over SSH with a key
  at the moment it writes the file, which is the proof that key authentication
  works on this host.
- Root does need one. The role reads `/root/.ssh/authorized_keys` and refuses to
  set `prohibit-password` if it is missing or empty — on such a host the
  password *is* root's only way in, and switching it off would remove the
  break-glass rather than harden it.

Quote the value if you set it to `yes` or `no` — YAML reads both as booleans,
and the role asserts on that before writing anything.

`sshd -T` does not always print back what the file says. OpenSSH keeps
`PermitRootLogin` as a table where several names share one value and prints the
first name matching it; at the OpenSSH versions on Debian 12 and 13 that table
lists `without-password` before `prohibit-password`, so the config we write
reads back under the older spelling. Upstream has since swapped the two, which
is why `vars/main.yml` maps each setting to a *list* of acceptable renderings
rather than one string.

Afterwards `sshd -T` is read back, as for the CA. It matters more here: a
drop-in sshd never included leaves the host accepting passwords while
everything else says otherwise. A missing CA merely fails to add a way in; this
fails to *remove* one, which is the failure that looks like success.

Two callers apply it.
[playbooks/provision-node.yml](../../playbooks/provision-node.yml) sets the flag
inside its base-system play, so a node is locked down as it is built — safe
there because that play is already connected with the automation key, and the
bootstrap play before it reached root by key.
[playbooks/ssh-lockdown.yml](../../playbooks/ssh-lockdown.yml) is for nodes that
already exist, one host at a time. A reload does not drop the connection it runs over, so open a
fresh session to the host before moving on.

## Presenting a host certificate

The fourth optional job, and the other direction of the same CA. `TrustedUserCAKeys`
lets the node believe a user; `HostCertificate` lets a user believe the node.

Off unless the role is given an OpenBao token and at least one domain. The node
cannot reach OpenBao, so the signing request is delegated to the controller —
the node only reads its own public host key and receives the certificate back.

**Connect by name or this does nothing.** OpenBao matches host principals
against `allowed_domains` and nothing else, so a certificate can never cover a
bare address. A node reached by IP is verified the old way whatever it presents.

Clients need one line in `known_hosts`, and until it is there nothing changes
for them:

```
@cert-authority *.mesh.example,*.public.example ssh-rsa AAAA…  # the key at infra/ssh_ca
```

### When it re-signs

Two conditions, and the second is the one that is easy to miss:

- fewer than `ssh_hardening_host_cert_renew_days` remain, or
- a principal the host should claim is absent from the certificate.

A certificate keeps working after the fleet moves to a different domain — still
signed, still unexpired — while naming something nobody types any more. Expiry
alone would never notice.

An **extra** principal is left alone on purpose. During a domain move the old
name must keep working until every client has been re-pointed, and re-signing it
away is exactly what would break that overlap.

The remaining life is measured **on the node**, with its own `ssh-keygen` and
its own clock. Parsing the timestamp on the controller would compare one local
time against another, and the fleet does not share a timezone — a mistake that
would surface months later as a certificate renewed early or not at all.

### Renewal is not scheduled

The certificate is refreshed when this role runs, and the role runs when
somebody asks it to. Ninety days is chosen to make that gap survivable, not to
make it correct. A periodic template is the fix and it does not exist yet.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ssh_hardening_mesh_port` | `automation_ssh_port` (2200) | Additional sshd port for automation over the mesh; shared with the ufw role via group_vars/all |
| `ssh_hardening_public_port` | `22` | The host's canonical public sshd port kept in the drop-in; override on hosts deliberately off 22 |
| `ssh_hardening_ca_public_key` | `""` | Fleet CA public key (`infra/ssh_ca` in OpenBao). Empty leaves sshd's credentials untouched; a value installs certificate trust alongside `authorized_keys` |
| `ssh_hardening_ca_path` | `/etc/ssh/trusted-user-ca.pub` | Where that key is written. Public by construction, world-readable |
| `ssh_hardening_disable_password_auth` | `false` | Retire password auth and password root login. Off by default — the one setting here that can lock everyone out |
| `ssh_hardening_permit_root_login` | `prohibit-password` | What root may do once passwords are gone. `no` closes the key path too and needs a deliberate replacement |
| `ssh_hardening_openbao_token` | `""` | Token used to sign this host's key. Empty leaves host identity untouched |
| `ssh_hardening_host_domains` | `[]` | Domains this host claims, one principal each as `<inventory_hostname>.<domain>` |
| `ssh_hardening_host_cert_renew_days` | `30` | Re-sign once fewer than this many days remain |
| `ssh_hardening_host_cert_path` | `/etc/ssh/ssh_host_ed25519_key-cert.pub` | Where the certificate is written |

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
