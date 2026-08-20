*(Russian version: [README.ru.md](README.ru.md))*

# openbao

## Description

Deploys [OpenBao](https://openbao.org/) on the panel host via Docker Compose,
with integrated Raft storage. OpenBao is the runtime secret store this fleet is
migrating to (issue #2); `ansible-vault` stays for repo-bound secrets.

**This role deploys and nothing more.** `bao operator init` prints the unseal
shares and the root token exactly once — they must never pass through Ansible,
a Semaphore log, or this repository, so the operator runs it. Re-running the
role against an initialised store is safe: nothing here touches init or unseal.

### Two things to know before using it

**Every restart seals the store.** Unsealing is manual (Shamir, 3 of 5 — the
decision recorded in #2). A config change fires the restart handler, the
container comes back sealed, and every playbook that reads a secret fails until
someone supplies the shares. A config change here is an operational event, not
a routine apply. A host reboot has the same effect.

**`disable_mlock` is forced on, and that is a trade-off.** The official image
ships no `setcap` and runs as the unprivileged `openbao` user, so the process
cannot lock memory even with `--cap-add=IPC_LOCK`; leaving mlock enabled makes
it refuse to start. The consequence is that memory holding decrypted secrets
can be written to swap. Mitigate on the host: zram keeps swapped pages in RAM
(see the `common` role), disk swap does not.

## Variables

| Variable | Default | Purpose |
|---|---|---|
| `openbao_image` | `ghcr.io/openbao/openbao:2.6.1` | Pinned image. Release tags carry a leading `v`; image tags do not. |
| `openbao_container_name` | `openbao` | Container name. |
| `openbao_restart_policy` | `unless-stopped` | Docker restart policy. |
| `openbao_data_dir` | `/opt/openbao` | Host directory for the compose file and the rendered config. |
| `openbao_bind_address` | `127.0.0.1` | Host address the API port is published on. Loopback only — for `docker exec` and the UI reverse proxy. Container clients use the network instead. |
| `openbao_port` | `8200` | API port. |
| `openbao_network` | `openbao-net` | Shared Docker network for container clients. Empty disables it. |
| `openbao_cluster_port` | `8201` | Raft cluster port. Not published; single node. |
| `openbao_node_id` | `{{ inventory_hostname }}` | Raft node id. Must stay stable across restarts. |
| `openbao_ui` | `true` | Serve the web UI. |
| `openbao_log_level` | `info` | Server log level. |
| `openbao_disable_mlock` | `true` | See above — required, not preferred. |
| `openbao_allow_root_generation` | `false` | Break-glass. Opens the unauthenticated root-generation endpoints, which OpenBao disables by default since 2.5.3. See below. |

### How clients reach it

Container clients (today: Semaphore, which reads secrets on behalf of
playbooks) join `openbao_network` and address the API by service name —
`http://openbao:8200`. The role creates that network itself, so the name has no
compose project prefix and the `semaphore` role can join it via
`semaphore_external_network`.

The published loopback port is **not** the path for containers. A port bound to
`127.0.0.1` is unreachable from a container; publishing on the bridge gateway
instead would expose the secret store to every container on the host. A
dedicated network is reachable only by containers explicitly joined to it.

Raft data lives in the named Docker volume `openbao_file`, mounted at
`/openbao/file` — **not** in `openbao_data_dir`, which holds only the compose
file and the rendered config.

The mount point is not arbitrary. Docker seeds a fresh named volume from the
image's directory, ownership included, so a path the image already declares
(`/openbao/file`) works. A path it does not declare yields a root-owned
directory, and the server — which runs as the unprivileged `openbao` user —
dies with `failed to open bolt file: permission denied`.

### Break-glass: getting a root token back

OpenBao **deprecated the unauthenticated root-generation endpoints in 2.5.3 and
disables them by default.** `bao operator generate-root -init` therefore answers
`403 permission denied`, and once the last root token is revoked there is no way
back to one without the procedure below. Verified on 2.6.1, the hard way.

Holding the unseal shares is necessary but **not sufficient**.

**`bao operator generate-root` does not work for this.** All three of its
subcommands call `/sys/generate-root-token/*`, and the switch opens
`/sys/generate-root/*` — a different path that stays 403. Drive the API
directly. Verified end to end on 2.6.1, 2026-08-04.

```bash
# 1. open the door; the container restarts and comes back SEALED
ansible-playbook playbooks/openbao.yml -e openbao_allow_root_generation=true
docker exec -it openbao bao operator unseal            # x3

# 2. start an attempt — note the nonce and the otp it returns
docker exec -it openbao bao write -f sys/generate-root/attempt

# 3. feed three shares. key=- reads from stdin, so the share never reaches
#    argv or shell history; read -rs keeps it off the screen too.
read -rs SHARE && printf '%s' "$SHARE" | docker exec -i openbao bao write sys/generate-root/update nonce=<nonce> key=- && unset SHARE
#    repeat x3; the third returns encoded_root_token

# 4. decode it yourself. `-decode` also calls the broken path, and this is only
#    base64 + XOR with the OTP.
python3 -c "
import base64
enc='<encoded_root_token>'; otp='<otp>'
raw=base64.b64decode(enc+'='*(-len(enc)%4))
print(''.join(chr(b^ord(o)) for b,o in zip(raw,otp)))
"

# 5. close the door again — a second restart and a second unseal
ansible-playbook playbooks/openbao.yml
docker exec -it openbao bao operator unseal            # x3
```

`encoded_root_token` and `encoded_token` are the same value under two names;
the first is a legacy alias.

**Treat the encoded token and the OTP as one secret.** Either alone is
useless, but together they *are* the root token — step 4 is arithmetic anyone
can run. Never store or transmit them through the same channel.

Two restarts and two unseals. Plan for the store to be unavailable meanwhile.

The switch stays off by default, matching upstream: while it is on, anyone who
can reach the API can *start* an attempt without a token. They cannot finish one
without a quorum of shares, so the exposure is nuisance rather than compromise —
but a permanent door for a once-a-year operation is a bad trade.

### Moving a secret out of ansible-vault

Both ends live on the panel, so the value never has to appear on screen or pass
through a clipboard — which also removes the chance of losing a character to
line wrapping. A long JWT is unselectable by hand in practice.

**One field:**

```bash
cd /opt/infra-inventory && ansible-vault view group_vars/all/vault.yml | python3 -c "import sys,yaml; sys.stdout.write(str(yaml.safe_load(sys.stdin)['vault_netbird_setup_key']))" | docker exec -i openbao bao kv put infra/netbird setup_key=-
```

`yaml.safe_load` parses the file properly whichever way the value is written —
quoted, or as a folded block over several lines. `str()` matters because a
numeric value (a chat id, a topic id) is not a string and would fail to write.

**Several fields — required whenever a secret has more than one:**

`bao kv put` REPLACES a secret wholesale. Writing field by field silently
discards everything written before it, so multi-field secrets go in one call,
as JSON on stdin:

```bash
cd /opt/infra-inventory && ansible-vault view group_vars/all/vault.yml | python3 -c "
import sys, json, yaml
v = yaml.safe_load(sys.stdin)
json.dump({
    'bot_token': str(v['vault_telegram_bot_token']),
    'chat_id': str(v['vault_telegram_chat_id']),
    'updates_topic_id': str(v.get('vault_telegram_updates_topic_id', '')),
}, sys.stdout)
" | docker exec -i openbao bao kv put infra/telegram -
```

A lone `-` in place of the key/value pairs makes the CLI read the whole secret
as JSON from stdin. Verified on 2.6.1 (2026-08-05, migrating hawser's five-host
table in one call). `bao kv patch` is the alternative when only some fields
should change.

**Verify without printing anything:**

```bash
docker exec -i openbao bao kv get -field=setup_key infra/netbird | tr -d '
' | wc -c
cd /opt/infra-inventory && ansible-vault view group_vars/all/vault.yml | python3 -c "import sys,yaml; print(len(str(yaml.safe_load(sys.stdin)['vault_netbird_setup_key'])))"
```

The two numbers must match. Use `docker exec -i`, never `-it`: with a TTY
allocated, the pty inserts carriage returns at wrap boundaries and the byte
count comes out too high.

**Adding a field to a secret that already has others:** use `kv patch`, not
`kv put`. Patch merges, so fields can go in one at a time — which with `put`
would silently discard whatever was written before:

```bash
cd /opt/infra-inventory && ansible-vault view group_vars/control/vault.yml | python3 -c "import sys,yaml; sys.stdout.write(str(yaml.safe_load(sys.stdin)['semaphore_access_key_encryption']))" | docker exec -i openbao bao kv patch infra/semaphore access_key_encryption=-
```

`kv patch` needs more than read/write on the data path. It performs a preflight
capability check, so its policy also needs:

```hcl
path "sys/internal/ui/mounts/*" { capabilities = ["read"] }
path "sys/capabilities-self"    { capabilities = ["update"] }
```

Without them the CLI fails with a 403 on `sys/internal/ui/mounts/...` that says
nothing about patching. Measured 2026-08-20, moving Semaphore's and Dockhand's
own credentials into the store.

Afterwards, confirm the pre-existing fields survived — if `api_token` is gone,
patch behaved like put and it must be restored before anything else proceeds:

```bash
docker exec openbao bao kv get -format=json infra/semaphore | python3 -c 'import sys,json;print(", ".join(json.load(sys.stdin)["data"]["data"].keys()))'
```

**What does not fit this recipe:** a value that is a mapping rather than a
scalar, such as hawser's per-host token table. That needs a layout decision
first — one field per host, or one KV path per host — not a transcription.

**The vault entry stays.** Deleting it is the last step of the whole migration,
after backups are real (#7), not part of moving an individual secret.

### Removing a field from a multi-field secret

Needed whenever a table accumulates entries for hosts that no longer exist.
Since `bao kv put` replaces a secret wholesale, a field is removed by writing
back everything except it — a read-modify-write in one pipeline, with the
surviving values passing through `python3` rather than across the screen:

```bash
docker exec -i openbao bao kv get -format=json infra/hawser | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']['data']
for k in ('lab-1', 'test'):
    d.pop(k, None)
json.dump(d, sys.stdout)
" | docker exec -i openbao bao kv put infra/hawser -
```

The tuple on the `for` line lists the fields to drop; `pop(k, None)` makes a
name that is already absent a no-op rather than an error. Confirm with
`bao kv get infra/hawser` — the named fields are gone and every other one still
holds its original value.

`bao kv patch` is the shorter form, but its default method requires the `patch`
capability, which `hawser-write` does not grant (see the policy in
`playbooks/openbao-setup.yml`). The explicit read-modify-write above works with
the policy as written.

**Removing a field is not erasing it.** KV v2 keeps previous versions, so the
old value stays readable at `bao kv get -version=<n> infra/hawser`. Pruning is
hygiene; a credential that actually leaked is dealt with by rotating it — the
token is replaced everywhere it is used — not by dropping it here.

## Dependencies

No `meta` dependencies, but Docker must already be present — apply the `docker`
role first. Uses the `community.docker` collection (`docker_compose_v2`,
`docker_container_exec`), pinned in `requirements.yml`.

## Example

```yaml
- name: Deploy OpenBao
  hosts: panel
  become: true
  roles:
    - openbao
```

**Not `hosts: control`.** The `controller` host is `ansible_connection: local`,
meaning "wherever Ansible is running" — the Semaphore *container* when a
template runs it, not the panel. This role must target the panel host itself.

Then, as the operator, once:

```bash
docker exec -it openbao bao operator init
```

Store the shares offline **and apart from any backup of the store** — a Raft
snapshot is encrypted with the master key, so snapshot and shares together are
the backup, and either one alone is worthless (#7).

After every restart:

```bash
docker exec -it openbao bao operator unseal   # repeat to the threshold
```

## Supported OS

Debian 12/13, Ubuntu current LTS. Enforced by an assert on `os_family`.
