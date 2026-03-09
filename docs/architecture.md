# Architecture

## Overview

`pyskills` follows a layered structure so behavior is easy to extend and
test.

```text
src/pyskills/
  cli/
    app.py
    commands/
  models/
  services/
  shared/
```

## Layers

- `pyskills.cli`
  - Click command surface and user output.
  - Delegates logic to services.
- `pyskills.models`
  - Pydantic data contracts and typed schemas.
  - Shared data structures across services and CLI.
- `pyskills.services`
  - Core business logic and orchestration.
  - Filesystem, network, parsing, installs, updates, consolidation.
- `pyskills.shared`
  - Shared constants and utility helpers.

## CLI Commands

- `add`: discover and install skills from local, git, and well-known
  sources.
- `list`: show installed skills and source metadata.
- `remove`: remove installed skills and update lock state.
- `find`: search remote catalog and optionally install results.
- `check`: check global lock-tracked skills for updates.
- `update`: reinstall outdated global lock-tracked skills.
- `lock-doctor`: inspect lock health.
- `adopt`: consolidate mixed skill layouts with dry-run/apply/undo.

Planned: `init` (scaffold SKILL.md), `install` (restore from lock file).

## Lockfiles

- Project lock: `skills-lock.json`
  - Tracks project-scoped installed skills.
- Global lock: `.agents/.skill-lock.json` (v2)
  - Tracks globally installed skills.
  - Includes `source_id`, `agents`, and `install_mode`.

## Consolidation Model

`adopt` scans known skill locations and classifies by skill name:

- `canonical`: already in canonical location.
- `needs-adoption`: exists outside canonical location.
- `duplicate`: same content appears multiple places.
- `conflict`: same skill name with different content.

Apply mode:

- copies/adopts to canonical location when needed,
- backs up replaced entries,
- writes a manifest in `.agents/.adopt-manifests`,
- supports rollback through `adopt --undo`.
