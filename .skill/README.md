# Claude Desktop Skill

This directory contains the Claude Desktop skill for the `ansible-playbooks` repository.

## Structure

```
.skill/
├── SKILL.md              # skill definition (triggers, workflow, quick reference)
├── references/
│   ├── CLAUDE.md              # mirror of root CLAUDE.md — DO NOT edit here
│   ├── workflow.md            # mirror of root references/ — DO NOT edit here
│   └── ansible-standards.md   # mirror of root references/ — DO NOT edit here
└── scripts/
    └── build.sh          # packages the .skill file for installation
```

## Important

**Never edit the files in `.skill/references/` directly.**
They are automatically synced from the root `CLAUDE.md` and `references/` by
`build.sh`. Always edit the root files and run `build.sh` to update the skill.

## Updating the skill

After any change to `CLAUDE.md`:

```bash
bash .skill/scripts/build.sh
```

Then in Claude Desktop:
Settings → Skills → Install from file → `ansible-playbooks.skill`

## Versioning

The skill version follows `CLAUDE.md` version.
Current: **v4.0**
