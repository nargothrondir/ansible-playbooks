#!/usr/bin/env bash
# spec-guards.sh — mechanical checks for the CLAUDE.md rules that ansible-lint
# cannot express. Per CLAUDE.md §13, a rule belongs in CI when a check for it
# is expressible; this script is where those checks live.
#
# Deliberately written in POSIX-ish bash with grep/sed only: it must be
# runnable on a workstation without Python or Ansible, so a rule is never
# "enforced" by something nobody can execute locally.
#
# Usage: bash .github/scripts/spec-guards.sh   (from the repository root)
# Exit:  0 = all guards pass, 1 = at least one violation
set -uo pipefail

FAILED=0
CHECKS=0

# In GitHub Actions, emit annotations; locally, plain text.
err() {
  if [ -n "${GITHUB_ACTIONS:-}" ]; then echo "::error::$1"; else echo "  ✗ $1"; fi
  FAILED=$((FAILED + 1))
}
ok()   { echo "  ✓ $1"; }
head_() { CHECKS=$((CHECKS + 1)); echo; echo "[$CHECKS] $1"; }

# --- 1. changed_when: true --------------------------------------------------
# `no-changed-when` only checks the key EXISTS, so `true` satisfies ansible-lint
# while masking real state (CLAUDE.md §6). Waiver: same-line `# spec-ok:`.
head_ "changed_when: true (CLAUDE.md §6 State reporting)"
hits=$(grep -rnE '^[[:space:]]*changed_when:[[:space:]]*["'"'"']?(true|yes|True|Yes)["'"'"']?[[:space:]]*(#.*)?$' \
        --include='*.yml' --include='*.yaml' roles/ playbooks/ 2>/dev/null | grep -v 'spec-ok:' || true)
if [ -n "$hits" ]; then
  while IFS= read -r l; do err "changed_when: true — use a register-based condition, or waive with '# spec-ok: <reason>': $l"; done <<< "$hits"
else ok "no unjustified changed_when: true"; fi

# --- 2. handlers declare listen: --------------------------------------------
head_ "every handler declares listen: (CLAUDE.md §6 Handlers)"
bad=0
for f in roles/*/handlers/main.yml; do
  [ -e "$f" ] || continue
  n=$(grep -cE '^- name:' "$f" || true)
  l=$(grep -cE '^[[:space:]]+listen:' "$f" || true)
  if [ "$n" != "$l" ]; then err "$f: $n handler(s) but $l listen: label(s) — every handler must declare listen:"; bad=1; fi
done
[ "$bad" = 0 ] && ok "all handlers declare listen:"

# --- 3. notify targets an existing listen label -----------------------------
head_ "notify references a listen label, not a handler name (CLAUDE.md §6)"
labels=$(grep -rhoE '^[[:space:]]+listen:[[:space:]]*.*' roles/*/handlers/main.yml 2>/dev/null \
         | sed -E 's/^[[:space:]]*listen:[[:space:]]*//; s/^["'"'"']//; s/["'"'"']$//' | sort -u)
bad=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  file="${line%%:*}"; rest="${line#*:}"; lineno="${rest%%:*}"
  val=$(echo "$line" | sed -E 's/.*notify:[[:space:]]*//; s/^["'"'"']//; s/["'"'"']$//')
  case "$val" in ""|"["*|"-"*) continue ;; esac   # skip list forms; checked by eye
  if ! grep -Fxq "$val" <<< "$labels"; then
    err "$file:$lineno notify \"$val\" matches no listen: label"; bad=1
  fi
done <<< "$(grep -rn 'notify:' roles/ --include='*.yml' 2>/dev/null || true)"
[ "$bad" = 0 ] && ok "every notify matches a listen: label"

# --- 4. noqa / spec-ok carry a reason ---------------------------------------
head_ "# noqa and # spec-ok carry a reason (CLAUDE.md §8)"
bad=0
while IFS= read -r l; do
  [ -z "$l" ] && continue
  err "bare '# noqa' without an explanation: $l"; bad=1
done <<< "$(grep -rnE '#[[:space:]]*noqa([[:space:]]*$|[[:space:]]+[^:])' --include='*.yml' --include='*.yaml' roles/ playbooks/ 2>/dev/null || true)"
while IFS= read -r l; do
  [ -z "$l" ] && continue
  err "'# spec-ok' without a reason after the colon: $l"; bad=1
done <<< "$(grep -rnE '#[[:space:]]*spec-ok[[:space:]]*($|[^:])' --include='*.yml' --include='*.yaml' roles/ playbooks/ 2>/dev/null || true)"
[ "$bad" = 0 ] && ok "all suppressions carry a reason"

# --- 5. README pairing ------------------------------------------------------
head_ "bilingual README pairs (CLAUDE.md §1)"
bad=0
[ -f README.md ] && [ ! -f README.ru.md ] && { err "README.md has no README.ru.md pair"; bad=1; }
for d in roles/*/; do
  r="${d}README.md"
  [ -e "$r" ] || { err "${d} has no README.md (CLAUDE.md §11)"; bad=1; continue; }
  [ -e "${d}README.ru.md" ] || { err "${r} has no README.ru.md pair"; bad=1; }
done
[ "$bad" = 0 ] && ok "every README has its pair"

# --- 6. role README required sections ---------------------------------------
head_ "role README sections: Description/Variables/Dependencies/Example/Supported OS (§11)"
bad=0
for r in roles/*/README.md; do
  [ -e "$r" ] || continue
  for s in Description Variables Dependencies Example "Supported OS"; do
    grep -qE "^##[[:space:]]+$s" "$r" || { err "$r: missing section '## $s'"; bad=1; }
  done
done
[ "$bad" = 0 ] && ok "all role READMEs carry the required sections"

# --- 7. root README index completeness --------------------------------------
head_ "root README indexes every role and playbook, in both languages (§5)"
bad=0
for idx in README.md README.ru.md; do
  [ -e "$idx" ] || continue
  for d in roles/*/; do
    name=$(basename "$d")
    grep -q "roles/$name/" "$idx" || { err "$idx does not list role '$name'"; bad=1; }
  done
  for p in playbooks/*.yml; do
    grep -q "$p" "$idx" || { err "$idx does not list '$p'"; bad=1; }
  done
done
[ "$bad" = 0 ] && ok "both indexes are complete"

# --- 8. .skill/ mirrors match their source ----------------------------------
head_ ".skill/references mirrors are in sync (build.sh transform)"
bad=0
# CR is stripped on both sides: a Windows checkout (autocrlf) must not report a
# mirror as stale when only the line endings differ.
if [ -f CLAUDE.md ] && [ -f .skill/references/CLAUDE.md ]; then
  if ! diff -q <(sed -e 's|](references/|](|g' -e 's|\[references/|[|g' CLAUDE.md | tr -d '\r') \
                 <(tr -d '\r' < .skill/references/CLAUDE.md) >/dev/null; then
    err ".skill/references/CLAUDE.md is stale — run .skill/scripts/build.sh"; bad=1
  fi
fi
for f in references/*.md; do
  [ -e "$f" ] || continue
  m=".skill/references/$(basename "$f")"
  [ -e "$m" ] || { err "$m is missing — run .skill/scripts/build.sh"; bad=1; continue; }
  diff -q <(tr -d '\r' < "$f") <(tr -d '\r' < "$m") >/dev/null \
    || { err "$m is stale — run .skill/scripts/build.sh"; bad=1; }
done
[ "$bad" = 0 ] && ok "skill mirrors match the source"

# --- 9. §N cross-references point at real sections --------------------------
head_ "CLAUDE.md §N references resolve"
bad=0
secs=$(grep -oE '^## [0-9]+\.' CLAUDE.md 2>/dev/null | grep -oE '[0-9]+' | sort -un)
# TRACKED FILES ONLY. A recursive filesystem walk also descends into sibling
# git worktrees under .claude/worktrees/, which hold OLD checkouts — producing
# failures locally that CI (where no worktrees exist) never sees. A check that
# behaves differently on a workstation than in CI is worse than no check.
refs=$(git ls-files -- '*.yml' '*.yaml' '*.md' '*.sh' 2>/dev/null \
        | xargs grep -hoE '§[0-9]+' 2>/dev/null | grep -oE '[0-9]+' | sort -un)
for n in $refs; do
  grep -qx "$n" <<< "$secs" || { err "reference to §$n but CLAUDE.md has no section $n"; bad=1; }
done
[ "$bad" = 0 ] && ok "all §N references resolve"

# --- 10. meta/main.yml with min_ansible_version -----------------------------
head_ "every role has meta/main.yml with min_ansible_version (§10)"
bad=0
for d in roles/*/; do
  m="${d}meta/main.yml"
  [ -e "$m" ] || { err "${d} has no meta/main.yml"; bad=1; continue; }
  grep -q 'min_ansible_version' "$m" || { err "$m has no min_ansible_version"; bad=1; }
done
[ "$bad" = 0 ] && ok "all roles declare meta and min_ansible_version"

# --- 11. requirements.yml is pinned -----------------------------------------
head_ "requirements.yml pins every dependency (§10)"
bad=0
if [ -f requirements.yml ]; then
  while IFS= read -r l; do
    [ -z "$l" ] && continue
    err "floating reference in requirements.yml: $l"; bad=1
  done <<< "$(grep -nE 'version:[[:space:]]*["'"'"']?(main|master|latest|HEAD)' requirements.yml || true)"
  names=$(grep -cE '^[[:space:]]*-[[:space:]]*name:' requirements.yml || true)
  vers=$(grep -cE '^[[:space:]]*version:' requirements.yml || true)
  [ "$names" != "$vers" ] && { err "requirements.yml: $names entries but $vers version: pins — every entry must be pinned"; bad=1; }
fi
[ "$bad" = 0 ] && ok "all dependencies pinned"

# --- 12. no play targets the `control` GROUP --------------------------------
# `controller` is ansible_connection: local — "wherever Ansible runs". From the
# panel CLI that is the panel; from a Semaphore template it is the Semaphore
# container. A play that installs software then deploys it into that container
# and reports success, which is a wrong result shaped exactly like a right one
# (#96, #97). Name the host, or take a `*_target` variable defaulting to it.
#
# `hosts: controller` is untouched and legitimate: API-only plays whose target
# genuinely IS the machine running Ansible. Only the GROUP is forbidden, so the
# pattern is anchored to end-of-line — "controller" must not match.
head_ "no play targets the control group (CLAUDE.md §6 / #96)"
hits=$(grep -rnE '^[[:space:]]*hosts:[[:space:]]*["'"'"']?control["'"'"']?[[:space:]]*(#.*)?$' \
        --include='*.yml' --include='*.yaml' playbooks/ 2>/dev/null | grep -v 'spec-ok:' || true)
if [ -n "$hits" ]; then
  while IFS= read -r l; do err "hosts: control targets the Ansible runner, not the panel — name the host or use a *_target variable: $l"; done <<< "$hits"
else ok "no play targets the control group"; fi

# --- 13. task names carry at most one Jinja expression, at the end ----------
# ansible-lint's name[template] already enforces this, so this is a duplicate —
# deliberately. ansible-lint cannot run on the Windows workstation, so CI is the
# only gate there, and this mistake has now cost three round trips of push,
# wait, fail. One grep pays for itself.
#
# Two ways to break it: more than one expression, or one that is not last.
head_ "task name: at most one Jinja expression, at the end (ansible-lint name[template])"
_names=$(grep -rnE '^[[:space:]]*-?[[:space:]]*name:.*\{\{' \
          --include='*.yml' --include='*.yaml' roles/ playbooks/ 2>/dev/null | grep -v 'spec-ok:' || true)
hits=$(printf '%s\n' "$_names" | grep -E '\{\{.*\{\{' || true)
hits="$hits
$(printf '%s\n' "$_names" | grep -vE '\}\}["'"'"']?[[:space:]]*$' || true)"
hits=$(printf '%s\n' "$hits" | grep -vE '^[[:space:]]*$' | sort -u || true)
if [ -n "$hits" ]; then
  while IFS= read -r l; do err "task name must end with a single Jinja expression: $l"; done <<< "$hits"
else ok "all templated task names are well formed"; fi

# --- 14. role READMEs quote the pinned version that defaults actually holds --
# Renovate bumps `defaults/main.yml`; the README variable tables restate the
# same value in prose and are never touched. Found three roles drifted at once
# during the pre-publication read-through — semaphore by two minor versions,
# dockhand by four patches, hawser by twenty. Nobody noticed because nothing
# looks broken: the role installs the right thing and only the documentation
# lies.
#
# Checked only where the README already documents the variable — a README that
# does not mention an image cannot be wrong about it.
#
# PAIRED WITH renovate.json, and it does not work without it. This guard first
# ran against a Renovate pull request and failed it: the bot had updated
# defaults and could not know the README existed, so the check it could never
# satisfy blocked the merge — the same shape as requiring a path-filtered
# workflow. renovate.json therefore carries a second customManager for the
# README tables. Remove that manager and every dependency pull request becomes
# unmergeable.
head_ "role README pins match defaults/main.yml (Renovate moves one, not the other)"
_pin_hits=""
for _def in roles/*/defaults/main.yml; do
  [ -f "$_def" ] || continue
  _role=$(basename "$(dirname "$(dirname "$_def")")")
  while IFS= read -r _line; do
    [ -z "$_line" ] && continue
    _var=${_line%%:*}
    _val=${_line#*:}
    _val=$(printf '%s' "$_val" | tr -d ' "'"'" | tr -d '\r')
    [ -z "$_val" ] && continue
    case "$_val" in *'{{'*) continue ;; esac
    for _rm in "roles/$_role/README.md" "roles/$_role/README.ru.md"; do
      [ -f "$_rm" ] || continue
      grep -q "$_var" "$_rm" || continue
      grep -qF "$_val" "$_rm" && continue
      _pin_hits="$_pin_hits$_rm documents $_var but not its current value '$_val'
"
    done
  done <<< "$(grep -hE '^[a-z_]+_(image|version):' "$_def" 2>/dev/null || true)"
done
_pin_hits=$(printf '%s\n' "$_pin_hits" | grep -vE '^[[:space:]]*$' || true)
if [ -n "$_pin_hits" ]; then
  while IFS= read -r l; do err "$l"; done <<< "$_pin_hits"
else ok "role README pins match defaults"; fi

# --- verdict ----------------------------------------------------------------
echo
if [ "$FAILED" -gt 0 ]; then
  echo "FAILED: $FAILED violation(s) across $CHECKS guards"
  exit 1
fi
echo "OK: $CHECKS guards passed"
