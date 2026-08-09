# Roadmap

Planned improvements to `CLAUDE.md` and the `.skill/` package.

**Rule:** a new item enters this roadmap only when either:
- a failure mode has been observed **3+ times** in `OBSERVATIONS.md`, or
- a structural limitation becomes practically painful (not theoretically suboptimal)

Items are removed from this roadmap when they are implemented and the
corresponding `CLAUDE.md` version is released.

---

## Pending

### v4.1 — Validation scripts

**Trigger:** manual validation steps are skipped or incorrectly applied
in 3+ sessions.

**What:** add executable scripts so validation is one command, not a mental checklist.

```
.skill/scripts/
├── lint.sh                   # ansible-lint with correct flags for this stack
├── check.sh                  # ansible-playbook --check --diff
└── validate-structure.sh     # verify directory layout and README presence
```

**Partially delivered:** structure validation now runs in CI as
`.github/scripts/spec-guards.sh` (README pairing and required sections, index
completeness, meta/`min_ansible_version`, skill-mirror sync, §N references) —
do not rebuild it here. What remains are the convenience wrappers `lint.sh`
and `check.sh`.

**Observations:** see OBSERVATIONS.md (pending first entries)

---

### v4.2 — build.sh: automated skill packaging

**Trigger:** CLAUDE.md is updated but skill references fall out of sync
(i.e. the manual copy step is forgotten).

**What:** `build.sh` copies `CLAUDE.md` into `.skill/references/`, packages
the `.skill` file, and prints install instructions.

**Status:** `build.sh` scaffold already exists — needs implementation after
first sync failure is observed in practice.

**Observations:** see OBSERVATIONS.md (pending first entries)

---

### v5.0 — Specialised sub-skills

**Trigger:** the main skill is triggered for tasks where a specialised skill
would produce significantly better results. Expected after the repository
grows to 5+ roles.

**What:** split into focused skills following the pattern observed in
`leogallego/claude-ansible-skills`:

```
.skill/skills/
├── ansible-scaffold/         # interactive role generator
│   └── SKILL.md
├── ansible-review/           # code audit against CLAUDE.md rules
│   └── SKILL.md
└── ansible-debug/            # playbook failure diagnostics
    └── SKILL.md
```

**Observations:** see OBSERVATIONS.md (pending first entries)

---

## Completed

### v4.0 — Slim core + on-demand references (2026-08-02, PR #79)

**Shipped differently than planned.** The original entry proposed splitting
`CLAUDE.md` into ten themed files under `.skill/references/` with a
task-type → files loading map. What actually shipped is simpler: the core was
cut 878 → 248 lines by removing what the model applies by default and what
`ansible-lint` enforces, with the remaining depth in two files —
`references/workflow.md` and `references/ansible-standards.md` — read on
demand. No loading map was needed: the core is short enough to read whole.

The trigger held (the agent was reading 800 lines for one-line tasks), but the
diagnosis deepened during implementation: the real problem was not length, it
was that v3.6 was **selectively** followed — some rules were structurally
unfollowable and had been skipped for months. Hence the new §13, which
requires every rule to be *mechanized, cheap, or deleted*.

---

## Evolution Policy

- Do not add items to this roadmap proactively without observed failure modes.
- Do not implement roadmap items until the trigger condition is met.
- When implementing: update `CLAUDE.md`, run `build.sh`, tag the release.
- After implementation: move the item to the Completed section with the
  version number and date.
