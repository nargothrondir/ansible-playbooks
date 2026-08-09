# Workflow reference — action plans, assumptions, dependency impact

Companion to [CLAUDE.md](../CLAUDE.md) §3–§4. Read on demand — when drafting
a plan for a large or ambiguous change, not for every session.

## Assumption categorization

Illustrative, not exhaustive:

| Assumption | Category | Reason |
|------------|----------|--------|
| Default SSH port is 22 | Implementation | Standard default; does not affect role design |
| Package name for a tool on Debian | Implementation | Deterministic; resolvable from OS facts |
| Whether a role creates a user or expects one to exist | **Architectural** | Changes the role's responsibility boundary |
| Secrets from HashiCorp Vault vs `ansible-vault` | **Architectural** | Changes the entire secrets strategy |
| Which inventory group a playbook targets | **Architectural** | Changes the blast radius of the change |
| Whether a service is enabled at boot | Implementation | Operationally scoped; state and proceed |

When in doubt — ask: one clarifying question is cheaper than a rebuilt
architecture. But do not manufacture doubt to avoid a routine decision.

## Action plan formats

Low-risk (single file, no structural impact, no new dependencies) — one line:

> Action plan: Add `no_log: true` to the database task in
> `roles/postgres/tasks/main.yml`.

All other changes — four things, **sized to the change** (core §4: one terse
line each is the norm; the requirement is coverage, not ceremony):

1. **What changes** — bullet list
2. **Which files** — explicit list
3. **What depends on it** — see below; if nothing was checkable, say so
   explicitly
4. **What is assumed** — facts not found in the codebase; omit if none

Labels are translated into the user's language (they are structural markers,
not fixed terms). Approval is any unambiguous consent in the user's language;
intent is determined from context.

## Dependency-impact report

Assess: `defaults`/`vars` consumed elsewhere · template rendering after
removals/renames · handler notify labels · `meta` dependents · other roles
that depend on this role.

The format scales with blast radius (core §3). For a small edit, one line
carrying its evidence status is a complete report:

> Dependency impact: grepped `common_zram_size` — role-local, no other
> consumer (verified).

Example of a correct itemized report, for when the blast radius earns it:

```text
Dependency impact:
- defaults/vars: verified — no other role references bootstrap_ssh_port
- templates:     inspected within available context — only sshd.conf.j2 visible
- handlers:      verified — notify labels unchanged
- meta:          unable to verify — not in scope
- Other roles:   unable to verify — not in scope
```

Rules: never omit the *check* when modifying a role (the report itself may be
one line); never state a conclusion without a status; never claim
**verified** for a file that was not available in the session. Always choose
the strongest status the evidence supports.
