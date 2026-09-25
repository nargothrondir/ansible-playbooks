# AI Agent Guidelines for Ansible Playbook Development

*Version 4.1*
*Repository: Ansible Playbooks*
*Author: Senior DevOps Engineer*
*Last updated: 2026-09-25*

---

**What this repo is:** the Ansible half of a small self-hosted platform — it
provisions and maintains a fleet of low-RAM Debian VPS edge nodes plus the
control host that runs the application control panel, Semaphore and Dockhand.
Every host joins a private Netbird mesh, and admin surfaces are reachable only
through it. Ansible owns the *platform* layer; the application containers are
deployed from git by Dockhand (§12). Most changes here are role edits applied
to live nodes serving real users — treat production as production.

**How to read this:** everything below is what cannot be inferred from the
codebase itself — this repo's decisions, its workflow contracts, its safety
policy. Generic Ansible practice is left to your own judgment and to
`ansible-lint` in CI; a generic rule appears here only when discovering the
violation late would be expensive. Worked examples live in `references/`
(§14).

---

## 1. Language and operator instructions

- Communicate with the user in the user's language; determine intent
  (approvals included) from context, not keyword lists.
- ALL generated artifacts — code, comments, templates, variable files,
  READMEs, commit messages — are in English, regardless of the conversation
  language.
- READMEs are bilingual **paired files** when the user's language is not
  English: `README.md` (English) + `README.<lang>.md` (e.g. `README.ru.md`),
  cross-linked; never monolithic two-language files. README language is fixed
  by the first message of the session.
- Action-plan labels and structural markers are translated into the user's
  language.
- **Commands the operator will run** are written for someone who cannot see
  what you know: runnable as pasted, in execution order, each block followed by
  one line on what success looks like. A placeholder is named in the prose
  rather than left as `<angle brackets>` to be guessed at; a command that waits
  with no prompt says so; steps that need a merged change come after the merge,
  not inside the pull request that introduces it.

## 2. Rule priority

1. **Safety** — no secrets in git, `no_log` on credentials, no destructive
   operations without confirmation. Not overridable by user request.
2. **Correctness** — idempotency, valid YAML, passing lint and check mode.
3. **User request**
4. **Project rules** (this document)
5. **Style**

When remediating a safety violation *requires* a destructive step (e.g.
removing a committed secret), do it immediately, prefer the least destructive
remediation that fully resolves the issue, and report it in the action plan.
This is the only case where a §4 stop is skipped.

## 3. Before writing code

- Repository context is only what is actually available in the session. Do
  not invent or silently assume project facts — never hostnames/groups,
  variable values, endpoints, credentials, or undocumented architecture
  decisions.
- Assumptions that would NOT change behavior or architecture: state them in
  the action plan and proceed. Assumptions that WOULD (responsibility
  boundaries, secrets strategy, target groups / blast radius): stop and ask.
  Do not manufacture doubt to avoid a routine implementation decision.
- When modifying a role, check what depends on it — variables consumed
  elsewhere, template rendering, handler notify labels, meta dependents — and
  report what you found, **scaled to the change**: one line for a small edit
  ("grepped `common_zram_size`: role-local, no other consumer"), an itemized
  breakdown only when the blast radius earns it. Never state a conclusion
  without its evidence status — **verified** (opened it) · **inspected within
  available context** (partial) · **unable to verify** (not in scope) — and
  never claim *verified* for a file you did not actually read.
- **A subagent's report is evidence to check, not a verdict to adopt.** Open
  the `path:line` or URL it quotes before building on it — the agents here
  quote by contract, so the check is cheap. What you could not confirm is
  marked as such, with where you looked.
- Pre-existing violations found while working: style/project-rule — note and
  ask, do not silently fix; safety/correctness — fix immediately and note;
  missing mandatory artifacts (README, meta) — note and ask, do not
  auto-create.
- **Someone else's tool: read its documentation before designing, its source
  before calling.** They answer different questions, and mixing them up costs a
  whole cycle. Source says what a call *does* — the authoritative contract, and
  still the right place for field names and status codes. Documentation says
  what a feature is *for*, and only it can tell you the scenario is supported at
  all. A mechanism can be reachable, well-understood and completely wrong to use
  here: Dockhand's stack import was driven correctly through its API against a
  remote host it explicitly does not serve, and produced a record pointing at a
  file the tool can never open (#163).
- **"The tool does not support this" is a finding, and it belongs in the action
  plan.** The check above earns its keep by cancelling work, not by informing
  it — so it happens before the plan is written, and its answer can be *this
  cannot be built*. Reporting that costs one message; discovering it from
  behaviour costs the build, the debugging, the revert, and whatever the
  experiment broke on the way.
- **Where to read, in this order.** The vendor's **manual** for intent and the
  limits of support — the only source that can say *not for this scenario*, so
  it comes first, before the plan. The **upstream source at the version we
  actually run** for the contract: field names, status codes, real behaviour —
  and the only one that matches production, because manuals describe the current
  release while we are pinned. **Generated API docs (Context7)** to find *where*
  to look; they are built from `main` rather than our tag and the tier is
  quota-limited, so they are a lead, never the verdict. When manual and pinned
  source disagree, the source says what will happen and the manual says what is
  supported — an unsupported scenario that happens to work is still a defect
  waiting for the next upgrade.

## 4. Action plan, when to stop, and when it is done

Produce an action plan before any code, **sized to the change**. Low-risk
edit (single file, no structural impact, no new dependency): one line.
Anything else covers four things — **what changes · which files · what
depends on it · what is assumed** (drop the last if nothing is assumed). One
terse line each is the norm and is enough: the requirement is coverage, not
ceremony. A plan long enough to feel like paperwork is a plan that will be
skipped next time.

**Then keep going.** A plan is information, not a request. When a step does
not need the user, do it, and put the status note in the same message as the
next action. A new role, a new dependency, a change across many files — each
is a line in the plan, not a stop.

**Stop and ask only when the next step:**

- is **destructive** — deleting data, issues or a branch (other than the one
  just merged, §9), rewriting history, force-pushing;
- acts **outside this repository** — writing to OpenBao, the panel, Dockhand
  or Semaphore through their APIs; merging in `docker-stacks` (a merge there
  is a deploy) or in the inventory repository; anything that runs on the
  fleet;
- touches an **infra-wide file** (the inventory's `group_vars/all*`,
  `ansible.cfg`, `.ansible-lint`) or **weakens a check** (§8);
- rests on an assumption that **changes the architecture** (§3);
- cannot be taken without an answer only the user has.

Permission prompts for the destructive commands stay on in
`.claude/settings.json`, as a second line behind this list.

**Done means,** unless the task says otherwise:

- a change here: CI green, then squash-merged with its branch deleted — that
  merge is not a deploy and needs no approval — and the operator handed the
  commands that roll it out, each with what success looks like (§1);
- a change that reaches the fleet: proven on one node before the rest;
- a question: answered, with the evidence status of each claim (§3).

**Work of many steps keeps its checklist in `.claude/TASKS.md`** (gitignored:
the repository is public). Tick items as they finish, add what turns up. A
long run gets its older turns summarised; the file survives that, the
conversation does not.

**Report as done · found · needs from you.** The last part is never buried:
it is what the user acts on.

**Diff discipline:** modify only files the task requires; no opportunistic
cleanup, reformatting, or refactoring — even inside an already-open file.
Exception: one-line fixes to adjacent code required for correctness or
buildability, noted in the action plan and commit message.

## 5. Structure

```text
inventory/          # hosts.example.yml only — the real one is a separate private repo
roles/<name>/       # defaults/ vars/ tasks/ handlers/ templates/ files/ meta/ README.md
playbooks/          # orchestration only — no monolithic playbooks
requirements.yml    # pinned versions only (no main/master/latest)
.ansible-lint       # production profile; explicit warn_list/skip_list
```

- **The inventory is not in this repository** — it is a separate private one,
  and `ansible.cfg` points at it. `group_vars/` and `host_vars/` must stay
  siblings of the inventory file: Ansible resolves them relative to it, so a
  flattened layout leaves every variable *silently* undefined — hosts still
  report `ok` — instead of failing.
- A dedicated role for a distinct service or for logic reused across
  playbooks; general host-level tasks go to `common`/`bootstrap`. Split task
  files and import them from `tasks/main.yml`.
- The root `README.md` is the navigation index (roles / playbooks / inventory
  groups / stack tables). Creating a role or playbook without updating it in
  the same commit is prohibited.

## 6. Repository conventions

The opinionated choices an agent cannot infer:

- **Variables:** `defaults/main.yml` = user-overridable; `vars/main.yml` =
  internal constants, prefixed `_`. Every variable starts with the role name.
- **Handlers:** every handler declares `listen:`; `notify` references the
  listen label, never the handler `name:`. All service restarts/reloads go
  through handlers.
- **Tags:** every install/config/service task carries the matching tag
  (`install`, `config`, `service`; plus `debug`, `always`, `never`).
- **Idempotency beyond modules:** `uri` mutations and `command`/`shell` use
  **fetch-then-guard** — GET the current state, mutate only what is missing
  behind a `when:` guard; non-deterministic steps (key/id generation) sit
  behind the same guard. No unguarded mutating calls that fire on every run.
- **External state is created by the playbook that needs it, through the
  tool's API — never by hand in a UI.** A Dockhand environment, a Semaphore
  template, a DNS record, a panel node: whatever a run depends on, the run
  creates, idempotently by the rule above. A click leaves nothing in git, is
  absent from a rebuild, and is found when the rebuild fails (#77). This costs
  more than clicking and the API contract will be wrong at least once —
  undocumented fields, renamed between versions, silently accepted and
  dropped. Pay it: the alternative is state nobody can reconstruct.
- **A record in another system is found by a stable key, never by its display
  name.** Panel nodes by address, subscription hosts by inbound UUID, Beszel
  systems by their token. Display names are for people and get renamed by
  hand; a lookup by name then misses, and the next run creates a duplicate.
  Look up by name only what nothing but this repository ever names, such as a
  Semaphore template.
- **Privilege:** role-level `become: true`, not per-task repetition; escalate
  only where needed; `become_user` when not root.
- **Templates render, don't compute** — logic lives in variables and tasks,
  and values are never hardcoded in a template; parameterize them.
- **OS gate:** roles assert `os_family == 'Debian'` with a `fail_msg`.
  Supported targets: Debian 12/13, Ubuntu current LTS.
- **Errors:** `failed_when` with a specific condition — never
  `ignore_errors`. `block/rescue/always` only when a partial failure needs
  cleanup or fallback; a `rescue` must log `ansible_failed_result.msg`.
- **State reporting:** never `changed_when: true` — it unconditionally masks
  real state (`no-changed-when` only checks that `changed_when` *exists*, not
  that it is honest). Use a register-based condition, or `false` for
  read-only tasks. **CI enforces this** (`.github/scripts/spec-guards.sh`);
  when a task genuinely always changes state, waive it with a same-line
  `# spec-ok: <reason>` comment.
- **Debug tasks** only when the output drives conditional logic, precedes a
  destructive operation, or captures an otherwise-invisible result; always
  tagged `debug`.

## 7. Security

- No hardcoded secrets or plain-text credentials in any artifact. **Every
  secret lives in OpenBao**, read at run time through the AppRole — there is no
  second store and no encrypted file in any repository.
- **Infrastructure IP addresses are secrets** — public and mesh alike. They
  live in OpenBao and nowhere on GitHub: not in this repository, not in the
  private inventory, not in the archive, and not in an issue, a pull request,
  a commit message or a Telegram report. The fleet serves users against state
  censorship: an address found in a repository tied to this account, matched
  to the same address on a live server, is exactly the association a censor
  looks for — and a published address also invites scanning, brute force and
  DDoS. "Clients connect to it anyway" does not make it public; it makes it
  findable only by someone already looking. Hosts are addressed by mesh name,
  and inventories or issues are inspected by counting addresses, never by
  printing them.
- **The same holds for hosting provider names and our own domains**, and for
  the text around the code as much as the code: commit messages, pull-request
  titles and bodies. They identify the fleet as surely as an address. In
  anything public use placeholders — `[Provider]`, `example.com`. CI checks a
  pull request's title, body and commit messages with the same guard as the
  files (`pr-text-guard`; bot-authored pull requests excepted).
- A value that is genuinely not a secret (a port, a role id) belongs in plain
  group_vars: putting it in the store costs a round trip and buys nothing.
- `no_log: true` on any task handling credentials (passwords, tokens, API
  keys, private keys).

## 8. Validation

- `ansible-lint` (production profile) is the **mechanical gate**: it runs in
  CI on every push and a failure blocks the merge. Run it locally first when
  the controller has it — the Windows workstation does not, so there CI *is*
  the gate. Never report a local lint pass that did not happen; "pushed, CI
  will check" is the honest phrasing.
- `# noqa` and `# spec-ok` always carry a reason on the same line.
- **A failing check is satisfied by changing the code, not the check.** Widening
  a guard, or reaching for `# noqa`/`# spec-ok` to get past one, changes what
  that guard promises — so it needs its own plan, its own approval, and proof
  the guard still bites afterwards (re-run it against a case it must catch).
  CI failures can be fixed unattended, which is when this is easiest to get
  wrong and hardest to notice.
- Roles support `ansible-playbook --check`; Molecule where scenario coverage
  beyond check mode is warranted.
- **Before merging anything non-trivial, review the diff for blockers only:**
  file, line, why it is wrong, how to show it fails (`/code-review` does this).
  Style notes wait; a blocker found here is cheaper than one found on a node.

## 9. Commits, branches and issues

**Issues live in the private archive repository, not here.** This repository
became public from a history-free snapshot; the backlog stayed behind because
its issues carry addresses and screenshots. So `gh issue` needs
`--repo <owner>/ansible-playbooks-archive`, and a new issue is opened THERE —
including issues about code that lives here. A `#N` in a comment is provenance
for a decision, not a link a reader can follow. So a pull request body stands
on its own: it is written to be read without archive access, because for
everyone but you that is the only half of the record that opens.

Conventional Commits in English, **scope mandatory**:
`type(scope): Description` — types `feat|fix|refactor|docs|style|test|chore|build|ci|perf`;
scopes `role/<name>` · `playbook/<name>` · `inventory` · `ci` · `docs`.
Never mix refactoring with functional changes in one commit (noted one-line
adjacent fixes are the exception).

**A branch is deleted once it stops being needed** — merged or abandoned,
remote *and* local. Anything worth keeping belongs on `main` or in an issue,
not in a branch nobody will open again. Deleting the branch of a pull request
you just merged is part of done (§4); any other deletion is destructive and a
§4 stop. The two halves have different safety conditions, and **the branch of
an open pull request is never deleted**:

- **Local** — safe once every local commit also exists on a remote:

  ```bash
  git log --branches --not --remotes --oneline   # empty = nothing stranded
  ```

  Anything listed is unpushed work; deal with it before deleting.

- **Remote** — safe once the work is in `main`, or is consciously abandoned.
  The local check above does NOT establish this: a pushed-but-unmerged branch
  passes it while being the only copy of that work. Check the pull request
  (`gh pr view <n> --json state`), because squash-merged branches do not look
  merged to git — `git branch --merged` and a commit-count diff against `main`
  both report a squashed branch as unmerged.

Merging with `--delete-branch` covers the common case, but it fails silently
when the branch is checked out in a worktree — so confirm the branch is gone
rather than assuming.

## 10. Meta and dependencies

`meta/main.yml` defines role dependencies and `min_ansible_version`.
Everything in `requirements.yml` is pinned to a version tag or commit;
document version bumps in the commit message.

## 11. Role documentation

Each role ships `README.md` (+ the `README.<lang>.md` pair per §1) with:
Description · Variables · Dependencies · Example · Supported OS.

## 12. Deployment layers

One test decides where Dockerized software lives:

> **If Dockhand were down, must this container still come up on its own?**
> **Yes → Platform (Ansible). No → Workload (Dockhand From-Git).**

- **Workload:** application containers deploy as Dockhand From-Git stacks —
  compose lives in the `docker-stacks` repo, the pinned image tag in git IS
  the deployed version, merging the bump IS the deploy. Secrets are Dockhand
  secret env vars (`${VAR}` in compose), never committed. **Delivery is
  polling, and the hour is a decision:** each From-Git stack carries its own
  cron and Dockhand deploys it from git on that schedule — 09:00 UTC, an
  afternoon in Karaganda, set by `dockhand-stack.yml`. A bad deploy breaks the
  same whenever it lands; what the hour buys is somebody awake to see it. The
  gap between merging and rolling out is the feature.
  An inbound webhook is allowed only where the endpoint is already public for
  another reason AND the call is signature-verified; opening a port to gain one
  does not qualify. Dockhand has two and they are not interchangeable
  (measured 2026-08-19):
  `/api/git/webhook/{repo}` deploys a single stack named after the repository,
  which a multi-stack repo like docker-stacks does not have, so it changes
  nothing here; `/api/git/stacks/{id}/webhook` is the one that reaches a
  From-Git stack, at the price of a secret and a GitHub hook per stack.
  Whichever is in use, know which — a merge that quietly deploys nothing looks
  exactly like a merge that worked.
- **Platform:** the layer Dockhand itself stands on is Ansible-provisioned:
  the Docker engine, Dockhand, Hawser, Netbird, Vault.
- **DR path:** each workload SHOULD keep an Ansible role able to bring it up
  on a bare host (empty server → role deploys → Dockhand takes over
  lifecycle).
- **Exceptions:** a stack that genuinely does not fit MAY stay
  Ansible-managed — record the deviation as a GitHub issue explaining why.

## 13. Keeping this document enforceable

A rule that is routinely broken without consequence teaches that rules here
are optional — and that lesson spreads to the rules that actually protect the
fleet. So every rule in this document must be one of:

- **mechanized** — CI blocks the violation. Preferred; move rules here
  whenever a check is expressible. A mechanized rule then leaves this
  document, unless catching it only at CI time is expensive enough that one
  preventive line still pays for itself.
- **cheap** — followable in one line, every time, without ceremony.
- **deleted** — if it is neither, it does not belong here.

Applied without exception:

- **Practice and text never diverge.** If a rule cannot be followed as
  written (a gate the workflow structurally cannot pass), the rule is wrong
  and gets fixed in the same session it is noticed — not quietly skipped.
- **A violation that reaches `main` is evidence, not a lapse.** It means the
  rule was unmechanized and expensive. Mechanize it or drop it; do not simply
  restate it louder.
- **"Enforced elsewhere" must be verified against the enforcing tool** before
  a rule is removed. A false backstop is worse than no backstop —
  `changed_when: true` was once pruned on exactly that mistake.
- **Scale the process to the change.** Reports and plans are proportional to
  blast radius (§3, §4); ritual detached from risk is what erodes compliance.
- **Compliance is audited, not self-reported.** In-flight catches are a lower
  bound — the agent judging compliance is the one being judged — so never
  read "nothing was flagged" as "nothing was broken".

## 14. References — read on demand

| File | When to read |
|---|---|
| [references/workflow.md](references/workflow.md) | Drafting an action plan for a large or ambiguous change; assumption categorization; the dependency-impact report format |
| [references/ansible-standards.md](references/ansible-standards.md) | The worked ✅/❌ examples behind §6–§8 and the rationale for the conventions |

Do not load these by default — they exist for depth, not for every session.
