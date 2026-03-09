# CLI Reference

## Overview

Run commands from repo root:

```bash
PYTHONPATH=src .venv/bin/python -m pyskills <command> [options]
```

## add

Install skills from local paths, git sources, or well-known sources.

```bash
pyskills add <source> [--skill NAME] [--agent NAME]
              [--global] [--copy] [--list]
```

Examples:

```bash
# Install all discovered skills from local path
PYTHONPATH=src .venv/bin/python -m pyskills add ./skills-repo

# Install one skill for codex only
PYTHONPATH=src .venv/bin/python -m pyskills add ./skills-repo \
  --skill demo --agent codex

# List available skills without installing
PYTHONPATH=src .venv/bin/python -m pyskills add ./skills-repo --list
```

## list

List installed skills in project or global scope.

```bash
pyskills list [--global] [--agent NAME]
```

Examples:

```bash
PYTHONPATH=src .venv/bin/python -m pyskills list
PYTHONPATH=src .venv/bin/python -m pyskills list --global
PYTHONPATH=src .venv/bin/python -m pyskills list --agent codex
```

## remove

Remove skills and update lock entries.

```bash
pyskills remove [SKILL ...] [--agent NAME] [--global]
                [--all] [--yes]
```

Examples:

```bash
# Remove one skill (with confirmation)
PYTHONPATH=src .venv/bin/python -m pyskills remove demo

# Remove one skill without prompt
PYTHONPATH=src .venv/bin/python -m pyskills remove demo --yes

# Remove all project-scoped tracked skills
PYTHONPATH=src .venv/bin/python -m pyskills remove --all --yes
```

## find

Search remote skill catalog.

```bash
pyskills find <query> [--limit N] [--install]
```

Examples:

```bash
PYTHONPATH=src .venv/bin/python -m pyskills find review
PYTHONPATH=src .venv/bin/python -m pyskills find migration --limit 5
PYTHONPATH=src .venv/bin/python -m pyskills find lint --install
```

## check

Check global tracked skills for updates.

```bash
pyskills check [--verbose]
```

Examples:

```bash
PYTHONPATH=src .venv/bin/python -m pyskills check
PYTHONPATH=src .venv/bin/python -m pyskills check --verbose
```

## update

Update global tracked skills.

```bash
pyskills update [--dry-run] [--verbose]
```

Examples:

```bash
PYTHONPATH=src .venv/bin/python -m pyskills update --dry-run
PYTHONPATH=src .venv/bin/python -m pyskills update
```

## lock-doctor

Inspect lock health and warnings.

```bash
pyskills lock-doctor
```

Example:

```bash
PYTHONPATH=src .venv/bin/python -m pyskills lock-doctor
```

## adopt

Analyze or consolidate mixed skill layouts.

```bash
pyskills adopt [--global] [--skill NAME]
              [--apply] [--conflict POLICY]
              [--yes] [--undo MANIFEST]
```

Conflict policy options:

- `keep-existing` (default)
- `use-canonical`

Examples:

```bash
# Dry-run
PYTHONPATH=src .venv/bin/python -m pyskills adopt

# Apply all with no prompt
PYTHONPATH=src .venv/bin/python -m pyskills adopt --apply --yes

# Apply selected skills
PYTHONPATH=src .venv/bin/python -m pyskills adopt --apply \
  --skill demo --skill alpha

# Undo one apply run
PYTHONPATH=src .venv/bin/python -m pyskills adopt --undo \
  .agents/.adopt-manifests/adopt-YYYYMMDDHHMMSS.json
```
