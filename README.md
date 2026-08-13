# ansible-playbooks

[![Lint](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/lint.yml/badge.svg)](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/lint.yml)
[![Security](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/security.yml/badge.svg)](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/security.yml)
[![Molecule](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/molecule.yml/badge.svg)](https://github.com/nargothrondir/ansible-playbooks/actions/workflows/molecule.yml)

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

Personal Ansible playbooks for VPS provisioning and management.

## Stack

| Component | Details |
|-----------|---------|
| OS | Debian 12 → 13 on the fleet, Ubuntu LTS on the control host |
| Kernel | XanMod (BBRv3) on the nodes |
| DNS | systemd-resolved with DoT to chosen upstreams (roles/dns) |
| Mesh | NetBird — every host joins it; admin surfaces are reachable only through it |
| Containers | Docker Engine + Compose plugin |
| Container delivery | Dockhand (From-Git stacks, polling) with Hawser edge agents |
| Automation | Semaphore (Ansible web UI) |
| Monitoring | Beszel (agent + hub), btop |
| Host security | CrowdSec (SSH detection, nftables bouncer), ufw, key-only SSH |
| Secrets | OpenBao (runtime) · ansible-vault (legacy, being retired) |

## Roles

| Role | Purpose | Depends on |
|------|---------|------------|
| [bootstrap](roles/bootstrap/README.md) | Create the key-only `ansible` automation user and grant passwordless sudo | — |
| [dns](roles/dns/README.md) | Encrypted DNS for the host's own lookups: systemd-resolved + DoT, interface nameservers removed so it takes effect | — |
| [common](roles/common/README.md) | Install baseline packages (sudo, curl, wget, ...) | — |
| [docker](roles/docker/README.md) | Docker Engine + Compose plugin via the official repo | — |
| [xanmod](roles/xanmod/README.md) | Install the XanMod performance kernel | — |
| [netbird](roles/netbird/README.md) | Install the NetBird agent and join the mesh | — |
| [ufw](roles/ufw/README.md) | Host firewall: public 22/443, mesh-only service ports on wt0 | — |
| [ssh_hardening](roles/ssh_hardening/README.md) | Mesh-only sshd port (2200) for key-based automation | ufw |
| [crowdsec](roles/crowdsec/README.md) | SSH-only detection with progressive bans, nftables bouncer; central LAPI wiring laid in (inactive) | common |
| [upgrade](roles/upgrade/README.md) | `apt update` + `full-upgrade` + `autoremove`, reboot if required | — |
| [notify_telegram](roles/notify_telegram/README.md) | Send a message to a Telegram chat via the Bot API | — |
| [semaphore](roles/semaphore/README.md) | Deploy Semaphore (Ansible web UI) via Docker Compose | — |
| [dockhand](roles/dockhand/README.md) | Deploy Dockhand (Docker management UI) via Docker Compose | — |
| [hawser](roles/hawser/README.md) | Deploy the Hawser edge agent (for Dockhand) on a host | — |
| [beszel_agent](roles/beszel_agent/README.md) | Beszel monitoring agent (binary + systemd, WebSocket to the hub, no inbound port) | — |
| [openbao](roles/openbao/README.md) | OpenBao secret store (integrated Raft) on the panel host; init and unseal stay manual | — |

## Playbooks

| Playbook | Roles applied | Target group |
|----------|--------------|--------------|
| [playbooks/site.yml](playbooks/site.yml) | bootstrap (as root), upgrade (as `ansible`) | new_vps |
| [playbooks/update.yml](playbooks/update.yml) | upgrade + notify_telegram (report) | managed |
| [playbooks/semaphore.yml](playbooks/semaphore.yml) | semaphore | `semaphore_target` (default: panel) |
| [playbooks/dockhand.yml](playbooks/dockhand.yml) | dockhand | `dockhand_target` (default: panel) |
| [playbooks/hawser.yml](playbooks/hawser.yml) | hawser (hosts with a token) | managed |
| [playbooks/provision.yml](playbooks/provision.yml) | common, docker | lab |
| [playbooks/dns.yml](playbooks/dns.yml) | dns (encrypted resolver) | `dns_target` (default: lab) |
| [playbooks/common.yml](playbooks/common.yml) | common (re-apply the baseline) | `common_target` (default: lab) |
| [playbooks/crowdsec.yml](playbooks/crowdsec.yml) | crowdsec | fleet (except panel) |
| [playbooks/beszel.yml](playbooks/beszel.yml) | beszel_agent | fleet (except panel) |
| [playbooks/provision-node.yml](playbooks/provision-node.yml) | bootstrap, upgrade, ssh_hardening, common, dns, netbird, docker, xanmod, hawser, crowdsec, ufw, beszel_agent + panel API | (survey) |
| [playbooks/new-profile.yml](playbooks/new-profile.yml) | — (panel API call) | control |
| [playbooks/new-node.yml](playbooks/new-node.yml) | — (panel API call) | control |
| [playbooks/dns-record.yml](playbooks/dns-record.yml) | — (Cloudflare API; imported by provision-node.yml, or standalone) | `dns_target` (default: controller) |
| [playbooks/dockhand-environment.yml](playbooks/dockhand-environment.yml) | — (Dockhand API via the panel; imported by provision-node.yml, or standalone) | `dockhand_env_target` (default: controller) |
| [playbooks/dockhand-stack.yml](playbooks/dockhand-stack.yml) | — (Dockhand + panel APIs via the panel; deploys the node's From-Git workload stack) | `dockhand_stack_target` (default: controller) |
| [playbooks/semaphore-template.yml](playbooks/semaphore-template.yml) | — (Semaphore API call; creates missing task templates, never modifies existing ones) | `semaphore_template_target` (default: controller) |
| [playbooks/semaphore-survey.yml](playbooks/semaphore-survey.yml) | — (Semaphore API call) | control |
| [playbooks/semaphore-inventory-repo.yml](playbooks/semaphore-inventory-repo.yml) | — (Semaphore API call; report-only without arguments) | control |
| [playbooks/openbao.yml](playbooks/openbao.yml) | openbao | `openbao_target` (default: panel) |
| [playbooks/openbao-setup.yml](playbooks/openbao-setup.yml) | — (OpenBao API: KV, policy, AppRole; run from the panel CLI with a short-lived token) | `openbao_setup_target` (default: panel) |
| [playbooks/openbao-verify.yml](playbooks/openbao-verify.yml) | — (proves the AppRole → KV read chain; run from Semaphore) | `openbao_verify_target` (default: controller) |
| [playbooks/mesh-ssh-check.yml](playbooks/mesh-ssh-check.yml) | — (SSH-over-mesh connectivity check) | control → mesh peers |

## Scripts

| Script | Purpose |
|---|---|
| [scripts/verify-secret-migration.py](scripts/verify-secret-migration.py) | Compare every ansible-vault secret against its OpenBao counterpart. **Run before deleting the vault files** (#2, #7). Prints names and verdicts only — values are compared as truncated hashes. |

## Inventory

**The inventory is not in this repository.** Host addresses, mesh addresses,
service domains and SSH public keys identify specific machines, so they live in
a private repository and this one stays publishable.
[inventory/hosts.example.yml](inventory/hosts.example.yml) documents the
structure; `.github/scripts/tells-guard.sh` runs in CI and fails the build if an
address or an unknown domain reappears here.

Semaphore registers the private inventory as its own Repository entry, separate
from this one. For a local run, clone it beside this checkout and point Ansible
at it — `group_vars/` and `host_vars/` must stay siblings of the inventory file,
because Ansible resolves them relative to it and a flattened layout makes every
variable **silently** undefined:

```bash
ansible-playbook -i ../infra-inventory/hosts.yml playbooks/site.yml
```

| Group | Purpose |
|-------|---------|
| new_vps | Freshly provisioned servers pending bootstrap |
| managed | Bootstrapped hosts managed via the `ansible` user |
| control | The Ansible control node itself (local connection) |
| lab | Experimental/disposable hosts (no daily updates) |

## Authentication model

Authentication is **key-only**, with a **separate key per identity** (never
share one key across users) and no passwords stored anywhere:

- **root** is reached with your **admin** key, used only for first-contact
  bootstrap. Inject its public part into root at VPS creation (provider UI /
  cloud-init), or copy it once with
  `ssh-copy-id -i ~/.ssh/admin_ed25519.pub root@<host>`.
- The **`ansible`** user gets a **dedicated automation** key (authorized by
  bootstrap) and has its password locked. This key is used for all ongoing runs.

Runtime secrets live in **OpenBao**, deployed on the control host by the
`openbao` role and read at run time through an AppRole. `ansible-vault` files in
the private inventory are what remains of the previous arrangement and are being
retired. The Ansible controller must be Linux or WSL — Ansible does not run on
native Windows.

## Usage

1. Prepare two keys (you may reuse an existing personal key as the admin key):

   ```bash
   # admin key for root access (skip if you already have a personal key)
   ssh-keygen -t ed25519 -a 100 -f ~/.ssh/admin_ed25519 -C "admin@controller"
   # dedicated automation key for the ansible user
   ssh-keygen -t ed25519 -a 100 -f ~/.ssh/ansible_ed25519 -C "ansible@controller"
   ```

2. Make sure root accepts your **admin** public key: inject it at VPS creation,
   or run `ssh-copy-id -i ~/.ssh/admin_ed25519.pub root@<host>` once.
3. Put the **ansible** public key into `bootstrap_authorized_keys` in
   `group_vars/new_vps.yml` **of the private inventory repository**.
4. Add target hosts to the `new_vps` group in its `hosts.yml`.
5. Load the keys into ssh-agent and run the flow (private key paths are not
   stored in git):

   ```bash
   ssh-add ~/.ssh/admin_ed25519 ~/.ssh/ansible_ed25519
   ansible-playbook playbooks/site.yml
   ```

The first play connects as `root` (admin key) and creates the key-only
`ansible` user with sudo; the second play reconnects **as `ansible`**
(automation key) and upgrades the server, rebooting only when the running
kernel is no longer the newest installed one (`needrestart -b -k`, plus the
`/var/run/reboot-required` marker where Ubuntu creates it).

### Scheduled updates with Telegram report

[playbooks/update.yml](playbooks/update.yml) upgrades the `managed` hosts and
sends a single summary to Telegram from the controller. Provide the bot
credentials via ansible-vault:

```bash
# in the private inventory repository
ansible-vault create group_vars/all/vault.yml
# vault_telegram_bot_token: "123456:ABC-..."
# vault_telegram_chat_id: "123456789"

ansible-playbook -i ../infra-inventory/hosts.yml playbooks/update.yml --ask-vault-pass
```

## Agent specification

This repository follows a strict AI agent specification — see
[`CLAUDE.md`](./CLAUDE.md) (v4.0: a slim core with on-demand details in
[`references/`](references/)). The `.skill/` directory packages it as a
Claude Desktop skill; see [`.skill/README.md`](./.skill/README.md).

Development log: [`OBSERVATIONS.md`](./OBSERVATIONS.md) · roadmap:
[`ROADMAP.md`](./ROADMAP.md).

### Subagents

`.claude/agents/` defines four narrow helpers that run on a cheaper model.
They are delegated work whose output is **cheap to verify**, never work that
produces a judgement:

| Agent | Does | Returns |
|-------|------|---------|
| `repo-scout` | read-only search across the repo (the §3 dependency checks) | `file:line` evidence |
| `run-triage` | structure long Ansible/CI/diagnostic output | failures per host, recap, flags |
| `claim-checker` | verify a factual claim before it is written down | CONFIRMED / REFUTED / UNVERIFIABLE + quote |
| `upstream-facts` | fetch facts from upstream docs and releases | quotes with URLs |

Anything deterministic belongs in CI instead — see
[`.github/scripts/spec-guards.sh`](.github/scripts/spec-guards.sh).

## Authors

- [nargothrondir](https://github.com/nargothrondir) — author & maintainer
- Built in pair with **Claude** (Anthropic) as an AI assistant — see the
  `Co-Authored-By` trailers throughout the git history.

## Structure

```
ansible-playbooks/
├── CLAUDE.md               # AI agent specification (source of truth)
├── references/             # agent-spec details, read on demand
├── .claude/agents/         # narrow subagents (cheap model, verifiable output)
├── ROADMAP.md              # planned improvements to the spec
├── OBSERVATIONS.md         # log of observed agent behaviour
├── inventory/
│   └── hosts.example.yml   # structure only — the real inventory is private
├── roles/                  # 15 roles, one README pair each (see the table above)
├── playbooks/
│   ├── tasks/              # reusable task files (e.g. the OpenBao read)
│   └── templates/          # templates the playbooks render
├── scripts/                # operator tooling, not part of a run
├── requirements.yml        # pinned collections
├── ansible.cfg
├── .ansible-lint
├── .github/
│   ├── workflows/          # lint · security · guards · molecule · ci-alert
│   └── scripts/            # spec-guards.sh · tells-guard.sh
└── .skill/                 # Claude Desktop skill (mirror of CLAUDE.md)
```

Issue numbers in comments (`#122`, `#68`) point at this project's tracker,
which is not public: this repository was published from a history-free
snapshot and the backlog stayed in the private predecessor, because its issues
carry addresses and screenshots. They are kept as provenance for the decision a
comment explains, not as links to follow.

New issues are opened there too, so the split does not blur over time. This
repository's own tracker is left for anything filed from outside.
