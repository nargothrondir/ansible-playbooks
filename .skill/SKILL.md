---
name: ansible-playbooks
description: >
  Senior DevOps guidelines for writing, modifying, and reviewing Ansible
  playbooks, roles, and infrastructure code for a personal VPS stack
  (Debian 12/13, Docker, Netbird mesh, Dockhand, OpenBao, monitoring,
  user provisioning).

  Trigger when the user asks to write, modify, review, or refactor any
  Ansible code (playbooks, roles, tasks, handlers, templates, variables,
  inventory, ansible.cfg, requirements.yml); discusses Ansible role
  architecture or structure; or asks about automating any part of their
  VPS stack with Ansible (Debian upgrade, user creation, DoH, Netbird,
  Docker, SSH hardening, package management).

  Do NOT trigger for general DevOps questions without Ansible context
  (e.g. "how do I configure Netbird manually").

  Always read references/CLAUDE.md before producing any action plan or code.
---

# Ansible Playbooks Skill

This skill enforces a strict, production-grade workflow for all Ansible work.
It is built around a single source of truth:

> **Always read `references/CLAUDE.md` before producing any action plan or code.**

`references/CLAUDE.md` contains the full specification (v4.0, 348 lines).
Worked examples live in `references/workflow.md` and
`references/ansible-standards.md` — read those on demand.
This file is a navigation aid and quick reference only.

---

## Workflow at a Glance

Every task follows this sequence — no exceptions:

```
1. Read references/CLAUDE.md
2. Analyse the request (§3)
3. Produce an action plan (§4) — translated into the user's language
4. Wait for confirmation if required (§4 Confirmation Gate)
5. Write code following the conventions (§5–§7)
6. Validate (§8)
7. Commit (§9)
```

---

## Quick Reference — what the spec adds beyond good Ansible

This file is **navigational only**: it never states a rule the core spec does
not. Generic best practice (FQCN, `loop`, task naming, `var-naming`) is left
to `ansible-lint` in CI and to model defaults — see the core §14 references
for which is which. What the spec adds is the part no linter can infer:

### Repo-specific conventions (core §6)

1. **Handlers via `listen:`** — `notify:` references the listen label, never the handler name
2. **`no_log: true`** on every task touching credentials (core §7)
3. **fetch-then-guard** for `uri`/`command` — never an unguarded mutation
4. **never `changed_when: true`** — CI greps for it; waive with same-line `# spec-ok: <reason>`
5. **Deployment layer test** (core §12) — "if Dockhand were down, must this container still come up?"

### Confirmation Gate — always wait when (core §4)

- Creating a new role
- Adding/removing dependencies in `meta/main.yml` or `requirements.yml`
- Changing inventory structure or group layout
- Modifying more than 3 files in one task
- Any destructive operation
- Any change to `ansible.cfg` or `.ansible-lint`
- Any infra-wide file (e.g. `inventory/group_vars/all*`)

### Process, scaled to blast radius (core §3, §4, §13)

- Action plans and dependency-impact reports are **proportional**: one line
  for a small edit, itemized only when the blast radius earns it
- Never claim `verified` for a file you did not open
- Diff discipline: only files the task requires; no opportunistic cleanup
  (one-line adjacent fixes allowed, noted in the plan)

---

## Stack Reference

Target environment for this repository:

| Component | Details |
|-----------|---------|
| OS | Debian 12/13 (nodes), Ubuntu LTS supported |
| User provisioning | `ansible` automation user — key-only, passwordless sudo (created by bootstrap) |
| Networking | Netbird (mesh VPN); DoH via dnscrypt-proxy (planned — no role yet) |
| Containers | Docker (via official repo) |
| Container delivery | Dockhand From-Git stacks + Hawser edge agents (core §12) |
| Monitoring | Beszel (hub + per-node agents), btop |
| Secrets | OpenBao, the only store — daily snapshots, restore proven |
| Auth | SSH key only after bootstrap; password only for initial root login |

---

## Reference Files

`references/CLAUDE.md` — the core specification. Read it before every task.

| Task type | Primary sections |
|-----------|-----------------|
| New role or playbook | §3 Before writing code, §4 Action plan, §5 Structure |
| Modifying existing role | §3 Dependency impact, §4 Confirmation gate + diff discipline |
| Variables / handlers / tags / errors | §6 Repository conventions |
| Secrets | §7 Security |
| Committing, branch cleanup | §8 Validation, §9 Commits and branches |
| Handing steps to the operator | §1 Language and operator instructions |
| Documentation | §11 Role documentation |
| Docker deploy decisions | §12 Deployment layers |
| Changing the spec itself | §13 Keeping this document enforceable |

Read on demand (not upfront):

- `references/workflow.md` — action-plan formats, assumption categorization,
  the dependency-impact report format with a worked example.
- `references/ansible-standards.md` — the ✅/❌ examples behind the
  conventions (variables, listen labels, fetch-then-guard, failed_when,
  no_log, noqa, tags), plus which practices CI enforces vs which are model
  defaults.
