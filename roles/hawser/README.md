# Role: hawser

🇬🇧 English · [🇷🇺 Русский](README.ru.md)

## Description

Deploys the [Hawser](https://github.com/Finsys/hawser) agent (for
[Dockhand](https://github.com/Finsys/dockhand)) on a remote Docker host in
**edge mode** — the agent connects outbound to Dockhand over WebSocket, so no
inbound port/forwarding is needed (good for VPS/NAT and censored hosts).

Each host is a separate Dockhand environment with its **own token**.

## Where the compose file comes from

**This role does not render one.** The agent's compose lives in
[docker-stacks](https://github.com/nargothrondir/docker-stacks) under `hawser/`,
which is its single source; the role fetches it at a pinned commit and deploys it.

Two things about that are deliberate:

- **Fetched on the controller, not the node.** `raw.githubusercontent.com` is
  intermittently blocked where part of the fleet lives, and provisioning must not
  depend on a node reaching GitHub. Semaphore already cannot start a run without
  GitHub, so this keeps the dependency where it already exists.
- **Pinned by commit, not by branch.** A git hash is the content address, so the
  pin doubles as the integrity check and the platform layer never follows a
  moving `main`. Bumping `hawser_compose_ref` is how a compose change reaches the
  fleet — which keeps that change visible in this repository's history rather
  than only in another one.

**A merge is what delivers it.** Semaphore's `Sync Hawser` template auto-runs
when `ansible-playbooks` gains a commit on `main` — template option *Auto-run
task if new git commit have been found*, repository `ansible-playbooks`, check
interval 10 minutes. Renovate proposes the pin bump, you read the compose diff
and merge, and the next check delivers it. Nothing is exposed to the internet:
Semaphore asks GitHub, GitHub never calls in.

The watched repository is this one and not `docker-stacks`, deliberately. What
gets deployed is decided by `hawser_compose_ref`, which lives here; a commit over
there changes nothing until the pin moves. Watching `docker-stacks` would fire
runs that can only be no-ops and then — having recorded that commit as seen —
stay silent on the pin bump that actually matters.

Scope is held by the template's own `Limit`, currently `pl-1,controller`: the
automation reaches the lab node only, and the fleet is still delivered by hand.
`controller` belongs in that limit because the token-table play targets it;
without it the run fails on the guard in `playbooks/hawser.yml`.

Three things about that schedule are easy to trip over:

- It is created from the template form and carries no name, so it may not show up
  on Semaphore's Schedule page. Reopening the template is how you confirm it
  exists — the checkbox, repository and interval are read back from the schedule,
  not stored on the template.
- Saving the template form sends the schedule only `cron_format` and
  `repository_id`. A limit set on the *schedule* would be silently dropped, which
  is why the limit lives on the template instead.
- Clearing the checkbox does not disable the schedule. It deletes it.

**Never deploy that folder as a Dockhand From-Git stack.** Dockhand would tell the
agent to `compose up` the project containing the agent; it stops its own container
and the replacement is left in `Created`, because the process that would start it
was inside the container it just stopped. Measured on the lab node 2026-08-13; the
node was unmanaged until an Ansible run restored it.

Values are written to a `.env` beside the compose file, which compose reads
automatically. `TOKEN` lives only there — `0600` (root-only), written by a task
running with `no_log`, so it is neither world-readable nor logged.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `hawser_compose_ref` | _(pinned commit)_ | docker-stacks commit the compose is fetched from; bump to adopt a change |
| `hawser_compose_repo` | `https://raw.githubusercontent.com/nargothrondir/docker-stacks` | Raw base URL |
| `hawser_compose_path` | `hawser/docker-compose.yml` | Path within that repository |
| `hawser_compose_cache` | `/tmp/hawser-compose-<ref>.yml` | Controller-side scratch; the ref is in the name so a new pin cannot reuse old content |
| `hawser_dir` | `/opt/hawser` | Dir holding the agent compose file and its `.env` |
| `hawser_stacks_dir` | `/opt/hawser-stacks` | `STACKS_DIR` for Hawser-managed stacks |
| `hawser_request_timeout` | `120` | Agent `REQUEST_TIMEOUT` (s); upstream default 30 s cancels long cold deploys |
| `hawser_dockhand_url` | _(required)_ | Dockhand edge endpoint (`wss://…/api/hawser/connect`), set in `group_vars/all` |
| `hawser_token` | _(required, vaulted)_ | Per-host agent token (e.g. from a `hawser_host_tokens` mapping in `group_vars/managed/vault.yml`) |

## Dependencies

`community.docker` (for `docker_compose_v2`). Docker must be installed on the host.

## Example

```yaml
- name: Deploy Hawser
  hosts: managed
  become: true
  tasks:
    - ansible.builtin.include_role:
        name: hawser
      when: hawser_token | default('') | length > 0
```

## Supported OS

Debian (bookworm, trixie), Ubuntu (jammy, noble).
