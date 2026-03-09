# pyskills

`pyskills` is a Python CLI to discover, install, update, and manage
agent skills across project and global scopes.

## Who is this for

If you use agent tools like Codex, Claude Code, or Cursor and want a
single way to manage skills in your repo or user environment.

## Highlights

- Install skills from local folders, Git repos, and well-known hosts.
- Track installed skills through lockfiles.
- Update globally tracked skills.
- Consolidate mixed skill layouts safely with backup and undo support.

## Quick Start

```bash
# from the repo root
PYTHONPATH=src .venv/bin/python -m pyskills --help
```

## Common Commands

```bash
# Add skills from a local directory
PYTHONPATH=src .venv/bin/python -m pyskills add ./skills-repo

# Search remote catalog
PYTHONPATH=src .venv/bin/python -m pyskills find review

# List installed skills in the current project
PYTHONPATH=src .venv/bin/python -m pyskills list

# Check and update globally tracked skills
PYTHONPATH=src .venv/bin/python -m pyskills check
PYTHONPATH=src .venv/bin/python -m pyskills update

# Consolidation dry-run
PYTHONPATH=src .venv/bin/python -m pyskills adopt

# Apply consolidation without prompts
PYTHONPATH=src .venv/bin/python -m pyskills adopt --apply --yes

# Apply consolidation to selected skills
PYTHONPATH=src .venv/bin/python -m pyskills adopt --apply \
  --skill demo --skill alpha

# Undo one prior apply run
PYTHONPATH=src .venv/bin/python -m pyskills adopt --undo \
  .agents/.adopt-manifests/adopt-YYYYMMDDHHMMSS.json

# Remove one skill (asks for confirmation)
PYTHONPATH=src .venv/bin/python -m pyskills remove demo

# Remove without prompt
PYTHONPATH=src .venv/bin/python -m pyskills remove demo --yes
```

## Safety Notes

- `adopt --apply` writes a manifest for rollback.
- `remove` is confirmation-first unless `--yes` is provided.
- Skill names and paths are sanitized/validated before write operations.

## Documentation

- [CLI Reference](docs/cli.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Testing](docs/testing.md)
- [Maintainer Guide](docs/maintainers.md)
