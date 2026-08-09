# Ansible standards reference — worked examples

Companion to [CLAUDE.md](../CLAUDE.md) §6–§8: the ✅/❌ examples and rationale
behind the conventions. The rules themselves live in the core spec. Two
classes of generic practice are deliberately absent from the core:

- **Lint-enforced** — implemented rules the production profile activates, so
  CI blocks them (verified 2026-07-27 against ansible-lint's own
  `src/ansiblelint/data/profiles.yml` plus the `rules/` directory, per core
  §13): `fqcn` (production), `name` and `var-naming` (basic), `ignore-errors`
  and `no-changed-when` (shared). The production profile extends all the
  lower ones, so every rule above applies here.
- **Model defaults** — current-generation models do these unprompted, and CI
  does *not* actually stop them: `loop` over `with_*`, no unused `register`,
  `ansible.builtin` over `community.*` when an equivalent exists.

Two traps found while verifying, worth recording so the next prune does not
repeat them:

- **`use-loop` is listed in the production profile but does not exist.**
  Entries in `profiles.yml` carrying a `url:` to a GitHub issue are *planned*
  rules — `use-loop` points at issue 2204 and has no implementation file. A
  rule name appearing in a profile is not proof it is enforced; check
  `rules/` for the implementation too.
- **`only-builtins` is implemented but opt-in** — it is in no profile, so it
  is inactive here, and it forbids non-builtin modules outright rather than
  expressing the preference we actually hold.

Note also that the linter checks that `changed_when` *exists*, not that it is
honest: `changed_when: true` satisfies `no-changed-when` while masking real
state — which is why its prohibition lives in the core spec (§6) and is
backed by a dedicated CI guard, not here.

## Variables

```yaml
# defaults/main.yml — user may override these
nginx_port: 80
nginx_worker_processes: auto

# vars/main.yml — internal constants, underscore prefix, not for overriding
_nginx_config_dir: /etc/nginx
_nginx_pid_file: /run/nginx.pid
```

Every variable carries the role prefix: `nginx_port`, never a bare `port` —
unprefixed names collide silently across roles.

## Handlers — listen labels

```yaml
handlers:
  - name: Restart Nginx service
    listen: "restart nginx"
    ansible.builtin.service:
      name: nginx
      state: restarted

tasks:
  - name: Deploy Nginx config
    ansible.builtin.template:
      src: nginx.conf.j2
      dest: /etc/nginx/nginx.conf
    notify: "restart nginx"     # the listen label — never the handler name
```

Rationale: `listen` decouples the notification contract from the handler's
display name, so renaming a handler cannot silently break its subscribers.

## Fetch-then-guard (idempotency for uri / command)

```yaml
- name: Fetch existing items
  ansible.builtin.uri:
    url: "{{ api }}/items"
    method: GET
  register: items

- name: Create the item only if absent
  ansible.builtin.uri:
    url: "{{ api }}/items"
    method: POST
    body: "{{ {'name': item_name} }}"
  when: item_name not in (items.json.response | map(attribute='name') | list)
```

Non-deterministic steps (random keys, generated ids, timestamps) go behind
the same existence guard so they run only on first creation and the resource
stays stable across re-runs. An unguarded `uri` POST/PATCH/DELETE (or
`command`) that mutates external state on every run is prohibited.

## Error handling

```yaml
# failed_when with a specific condition — never ignore_errors
- name: Create user if not exists
  ansible.builtin.command: useradd {{ username }}
  register: result
  failed_when: result.rc != 0 and 'already exists' not in result.stderr
  changed_when: result.rc == 0
```

`ignore_errors: true` masks real failures with no recovery path.
`block/rescue/always` is for multi-step changes where a partial failure
leaves intermediate state needing cleanup or fallback — never for a single
task (use `failed_when`), and the `rescue` must log
`ansible_failed_result.msg`: a silent rescue is not error handling.

## OS assert

```yaml
- name: Assert supported OS family
  ansible.builtin.assert:
    that:
      - ansible_facts['os_family'] == 'Debian'
    fail_msg: >
      Unsupported OS: {{ ansible_facts['distribution'] }}
      {{ ansible_facts['distribution_version'] }}.
      Only Debian/Ubuntu are supported.
```

`assert` without `fail_msg` is prohibited — without it the error output
carries no context. Prefer `os_family` over distribution checks to cover
Debian and Ubuntu with one condition.

## no_log

```yaml
- name: Create database user
  community.mysql.mysql_user:
    name: "{{ db_user }}"
    password: "{{ db_password }}"
    state: present
  no_log: true      # mandatory on any credential-handling task
```

Without it, secret values appear in Ansible stdout and CI logs.

## Lint

`.ansible-lint` keeps `warn_list` and `skip_list` explicit (implicit defaults
are not allowed). Inline skips always carry a reason:

```yaml
- name: Run legacy init script
  ansible.builtin.command: /opt/legacy/init.sh  # noqa: command-instead-of-module — no module equivalent exists
  changed_when: false
```

## Tags

`install` / `config` / `service` on every task of the matching type; `debug`
on every debug task; `always` / `never` only by explicit design.
