#!/usr/bin/env bash
# tells-guard.sh — keep infrastructure identifiers out of the public repository.
#
# DESIGN NOTE, and the reason this is not a list of forbidden values:
# a guard that enumerated our real IPs and domains would publish them itself,
# inside the very repository it is meant to protect. So it checks the SHAPE of
# a leak instead: an IPv4 literal outside the documentation ranges, or a domain
# that is not a known upstream. Anything new forces a conscious decision rather
# than slipping through.
#
# Usage: bash .github/scripts/tells-guard.sh   (from the repository root)
set -uo pipefail

FAILED=0
err() { if [ -n "${GITHUB_ACTIONS:-}" ]; then echo "::error::$1"; else echo "  ✗ $1"; fi; FAILED=$((FAILED + 1)); }

# Files never scanned: binaries and vendored third-party content.
SCAN_EXCLUDE='\.(png|jpg|jpeg|ico|svg|webmanifest|woff2?|ttf)$'

# Tracked files only — a filesystem walk would also descend into sibling git
# worktrees under .claude/worktrees/. Piped through xargs -0 so the whole scan
# is ONE grep invocation rather than one per file: the per-file version took
# over two minutes on a Windows workstation, and a guard nobody can afford to
# run locally is not a guard.
scan_files() { git ls-files -z | tr '\0' '\n' | grep -vE "$SCAN_EXCLUDE" | tr '\n' '\0'; }

# --- public resolvers -------------------------------------------------------
# Addresses of PUBLIC DNS resolvers this project configures or documents
# (roles/dns). They are other people's infrastructure, not ours, and they are
# listed here rather than woven into the regexes below so that adding one is an
# obvious one-line edit instead of surgery on a pattern.
#
# The rule for this block is the same as for the domain allowlist: a resolver
# goes in when the role can actually be pointed at it. Nothing of ours belongs
# here, ever.
RESOLVER_V4='1\.1\.1\.1|1\.0\.0\.1|8\.8\.8\.8|8\.8\.4\.4|9\.9\.9\.9|149\.112\.112\.112|194\.242\.2\.2|193\.110\.81\.0|94\.140\.14\.14'
RESOLVER_V6='2606:4700:4700:|2620:fe:|2001:4860:4860:'

# --- 1. IPv4 literals ------------------------------------------------------
# Allowed: RFC 5737 documentation ranges, loopback, any/broadcast, and the
# public resolvers we legitimately configure.
echo "[1] IPv4 literals outside the documentation ranges"
# NOTE on 100.64.0.0: allowed as an exact literal only (the CGNAT range base,
# referenced in the CrowdSec mesh whitelist). The range 100.64/10 as a whole is
# NOT allowed — mesh addresses live inside it, so a blanket allow would let the
# very identifiers this guard exists to catch straight through.
ip_ok='^(192\.0\.2\.|198\.51\.100\.|203\.0\.113\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|127\.0\.0\.1$|127\.0\.1\.1$|0\.0\.0\.0$|255\.255\.255\.255$|100\.64\.0\.0$)|^('"$RESOLVER_V4"')$'
found=0
while IFS= read -r hit; do
  [ -z "$hit" ] && continue
  file="${hit%%:*}"; rest="${hit#*:}"; lineno="${rest%%:*}"; text="${rest#*:}"
  for ip in $(echo "$text" | grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b'); do
    echo "$ip" | grep -qE "$ip_ok" && continue
    err "$file:$lineno real-looking IP '$ip' — use an RFC 5737 range (203.0.113.x) or move it out of this repository"
    found=1
  done
done <<< "$(scan_files | xargs -0 grep -nE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' 2>/dev/null || true)"
[ "$found" = 0 ] && echo "  ✓ no real-looking IPv4 literals"

# --- 1b. IPv6 literals -----------------------------------------------------
# Section 1 matches four dot-separated octets and therefore never saw an IPv6
# address at all — a whole address family walked past the guard.
#
# Matching IPv6 naively is noisy, and in two distinct ways:
#
#   - `12:34:56`, MAC addresses and image digests look like colon groups. So a
#     hit only counts when it contains `::` or carries the full seven colons of
#     an uncompressed address. Times and MACs have neither.
#   - `::` also means scope resolution. `Acquire::Retries` in an apt config
#     yields `e::`, which is a syntactically valid IPv6 address and obviously
#     not one. So a hit also needs at least four hex digits — every real
#     address has them, a word ending in one hex letter does not.
echo
echo "[1b] IPv6 literals outside the documentation and private ranges"
# Allowed: loopback, unspecified, link-local, multicast, IPv4-mapped, the
# RFC 3849 documentation prefix, and unique-local (the IPv6 counterpart of the
# RFC 1918 ranges already allowed above).
ip6_ok='^(::1|::|::ffff:|fe80:|ff0[0-9a-f]:|2001:0?db8:|f[cd][0-9a-f]{2}:|'"$RESOLVER_V6"')'
found=0
while IFS= read -r hit; do
  [ -z "$hit" ] && continue
  file="${hit%%:*}"; rest="${hit#*:}"; lineno="${rest%%:*}"; text="${rest#*:}"
  for ip6 in $(echo "$text" | grep -oE '(([0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|::([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4})'); do
    # Not an address unless compressed (::) or fully written out (7 colons).
    case "$ip6" in *::*) ;; *)
      [ "$(echo "$ip6" | tr -cd ':' | wc -c)" -ge 7 ] || continue ;;
    esac
    # Not an address without real content: rules out Foo::Bar scope operators.
    [ "$(echo "$ip6" | tr -cd '0-9a-fA-F' | wc -c)" -ge 4 ] || continue
    echo "$ip6" | tr 'A-Z' 'a-z' | grep -qE "$ip6_ok" && continue
    err "$file:$lineno real-looking IPv6 '$ip6' — use 2001:db8:: or move it out of this repository"
    found=1
  done
# Candidate lines only: a compressed address, or an uncompressed one written
# out in full. Scanning every line with two colons made the guard several times
# slower for nothing — almost every YAML line has two colons.
done <<< "$(scan_files | xargs -0 grep -nE '([0-9a-fA-F]{1,4}::|::[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){7})' 2>/dev/null || true)"
[ "$found" = 0 ] && echo "  ✓ no real-looking IPv6 literals"

# --- 2. Domains ------------------------------------------------------------
# Allowed: documentation domains plus the upstreams this project genuinely
# talks to. Add to this list only when a NEW upstream is introduced — never to
# silence our own domain.
echo
echo "[2] domains outside the known-upstream allowlist"
# Only strings ending in a real TLD count as a domain. Without this, every
# dotted identifier in the codebase matches — `ansible.builtin.service`,
# `readme.ru.md`, `items.json.response` — and the guard drowns in noise.
# Kept deliberately short. Long TLD lists collide with ordinary identifiers —
# `page` matched the sysctl `vm.page-cluster`, `run`/`team` are worse.
#
# Two are excluded on purpose and must stay excluded: `md` would match every
# README.md and CLAUDE.md in the tree, and `sh` every shell script — including
# this file. Both would drown the guard in its own repository.
#
# The country codes are not decoration: the original list covered `ru` and `de`
# but not the other places this fleet has nodes, so a domain on any of them was
# invisible. `google` is here for the same reason — dns.google sat in the xray
# template and passed, which is what proved the hole rather than argued it.
TLDS='com|org|net|io|dev|cloud|site|ru|de|info|app|co|me|tech|xyz|cc|kz|pl|ua|by|su|eu|uk|nl|se|fi|tr|am|ge|uz|google|online|pro|top|space|store|shop|club|live|link|website|fun|click|pw|ws|sbs|cfd|host'
# Third-party IP-check services referenced inside the xray reality profile
# template. They are configuration values pointing at other people's sites, not
# our infrastructure — but they are still domains, so they are listed here
# explicitly rather than hidden by excluding the file.
IPCHECK_OK='|whoer\.net|browserleaks\.com|2ip\.io|2ip\.ru'

# Upstreams this project genuinely talks to, plus a few names that merely look
# like domains (containerd.io is a Debian PACKAGE name). Extend only for a NEW
# upstream — never to silence one of our own hostnames.
domain_ok='(example\.(com|org|net)|localhost|github\.com|githubusercontent\.com|github\.io|ghcr\.io|debian\.org|ubuntu\.com|docker\.com|docker\.io|containerd\.io|letsencrypt\.org|cloudflare\.com|netbird\.io|netbird\.cloud|crowdsec\.net|packagecloud\.io|xanmod\.org|ansible\.com|readthedocs\.io|python\.org|telegram\.org|mozilla\.org|openbao\.org|hashicorp\.com|angie\.software|sshaudit\.com|renovatebot\.com|beszel\.dev|semaphoreui\.com|w3\.org|schema\.org|dns\.google|cloudflare-dns\.com|quad9\.net|mullvad\.net|dns0\.eu|adguard-dns\.com'"$IPCHECK_OK"')$'
found=0
while IFS= read -r hit; do
    [ -z "$hit" ] && continue
    file="${hit%%:*}"; r="${hit#*:}"; lineno="${r%%:*}"; rest="${r#*:}"
    for d in $(echo "$rest" | grep -oiE "\b[a-z0-9][a-z0-9-]*(\.[a-z0-9][a-z0-9-]*)*\.($TLDS)\b" | tr 'A-Z' 'a-z' | sort -u); do
      # A match immediately followed by another dot is part of a longer dotted
      # identifier, not a domain: README.ru.md yields "readme.ru" because `ru`
      # is a TLD. grep -E has no lookahead, so this is checked after the fact.
      echo "$rest" | grep -qiE "$(echo "$d" | sed 's/\./\\./g')\." && continue
      echo "$d" | grep -qE "$domain_ok" && continue
      # Strip one label at a time so sub.github.com matches github.com.
      parent="${d#*.}"
      echo "$parent" | grep -qE "$domain_ok" && continue
      parent2="${parent#*.}"
      echo "$parent2" | grep -qE "$domain_ok" && continue
      err "$file:$lineno domain '$d' is not a known upstream — parameterize it, or use example.com"
      found=1
    done
done <<< "$(scan_files | xargs -0 grep -niE "\b[a-z0-9][a-z0-9-]*(\.[a-z0-9][a-z0-9-]*)*\.($TLDS)\b" 2>/dev/null || true)"
[ "$found" = 0 ] && echo "  ✓ no unknown domains"

# --- 3. Public SSH keys ----------------------------------------------------
# A public key is not a secret, but it is a unique fingerprint tying this
# repository to specific machines.
echo
echo "[3] SSH public keys"
found=0
while IFS= read -r hit; do
  [ -z "$hit" ] && continue
  echo "$hit" | grep -qE 'AAAA[A-Za-z0-9+/]{20}' || continue
  echo "$hit" | grep -qiE 'example|placeholder|molecule|AAAA\.\.\.' && continue
  err "${hit%%:*} contains a real SSH public key — it identifies specific machines; keep it with the inventory"
  found=1
done <<< "$(git grep -nE 'ssh-(ed25519|rsa) AAAA' -- . 2>/dev/null || true)"
[ "$found" = 0 ] && echo "  ✓ no real SSH public keys"

echo
if [ "$FAILED" -gt 0 ]; then
  echo "FAILED: $FAILED tell(s) would be published"
  exit 1
fi
echo "OK: no infrastructure tells found"
