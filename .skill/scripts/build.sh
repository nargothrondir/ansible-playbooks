#!/usr/bin/env bash
# build.sh — packages the Claude Desktop skill from the repository source
# Usage: bash .skill/scripts/build.sh [--output <path>]
# Output: ansible-playbooks.skill in the repository root (or --output path)
# Requires: bash, python3 (with PyYAML), zip, sed, awk

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SKILL_DIR="$REPO_ROOT/.skill"
OUTPUT="${1:---output}"
if [[ "$OUTPUT" == "--output" ]]; then
  OUTPUT_PATH="$REPO_ROOT/ansible-playbooks.skill"
else
  OUTPUT_PATH="$2"
fi

echo "=== ansible-playbooks skill builder ==="
echo "Repository root : $REPO_ROOT"
echo "Skill directory : $SKILL_DIR"
echo "Output          : $OUTPUT_PATH"
echo ""

# Step 1: sync CLAUDE.md and its reference files into the skill.
# Inside the skill, CLAUDE.md sits NEXT TO the reference files, so the core's
# "references/<file>" links are rewritten to plain "<file>" links — both the
# href and the visible link text.
echo "[1/4] Syncing CLAUDE.md + references/ → .skill/references/"
sed -e 's|](references/|](|g' -e 's|\[references/|[|g' \
  "$REPO_ROOT/CLAUDE.md" > "$SKILL_DIR/references/CLAUDE.md"
cp "$REPO_ROOT"/references/*.md "$SKILL_DIR/references/"
CLAUDE_LINES=$(wc -l < "$SKILL_DIR/references/CLAUDE.md" | tr -d ' ')
echo "      Done ($CLAUDE_LINES lines + $(ls "$REPO_ROOT"/references/*.md | wc -l | tr -d ' ') reference files)"

# Step 2: keep the version/line-count reference in SKILL.md in sync
echo "[2/4] Updating version reference in SKILL.md"
CLAUDE_VERSION=$(sed -n 's/^\*Version \(.*\)\*$/\1/p' "$REPO_ROOT/CLAUDE.md" | head -n1)
if [[ -z "$CLAUDE_VERSION" ]]; then
  echo "      ERROR: could not parse version from CLAUDE.md"
  exit 1
fi
sed -i.bak -E \
  "s/full specification \(v[0-9]+\.[0-9]+, [0-9]+ lines\)/full specification (v${CLAUDE_VERSION}, ${CLAUDE_LINES} lines)/" \
  "$SKILL_DIR/SKILL.md"
rm -f "$SKILL_DIR/SKILL.md.bak"
echo "      Done (v${CLAUDE_VERSION}, ${CLAUDE_LINES} lines)"

# Step 3: validate description length
echo "[3/4] Validating SKILL.md description length"
DESC_LEN=$(python3 -c "
import re, yaml, sys
content = open('$SKILL_DIR/SKILL.md').read()
match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
if not match:
    print('ERROR: no frontmatter found')
    sys.exit(1)
fm = yaml.safe_load(match.group(1))
desc = fm.get('description', '')
print(len(desc))
")
if (( DESC_LEN > 1024 )); then
  echo "      ERROR: description is $DESC_LEN characters (limit: 1024)"
  exit 1
fi
echo "      OK ($DESC_LEN / 1024 characters)"

# Step 4: package
echo "[4/4] Packaging .skill file"
rm -f "$OUTPUT_PATH"
cd "$REPO_ROOT"
zip -r "$OUTPUT_PATH" .skill/ --quiet
echo "      Done: $OUTPUT_PATH"
echo ""

echo "=== Build complete ==="
echo ""
echo "To install in Claude Desktop:"
echo "  Settings → Skills → Install from file → ansible-playbooks.skill"
