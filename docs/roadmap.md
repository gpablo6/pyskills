# Roadmap

## Status Legend

- `Done`: implemented and tested.
- `In progress`: partially implemented, active iteration.
- `Planned`: queued for upcoming work.

## Milestone 1: Core CLI + Safety (Current)

### Done

- Structured package layout: `models`, `services`, `cli`, `shared`.
- Source parsing for `local`, `github`, `gitlab`, `git`, `well-known`.
- Core commands:
  - `add`, `list`, `remove`, `find`, `check`, `update`, `lock-doctor`.
- Global lock fidelity improvements (v2 migration and metadata fields).
- Consolidation workflow:
  - `adopt` dry-run
  - `adopt --apply` (backup-first)
  - `adopt --undo` (manifest rollback)
  - selective targeting via `--skill`
- Destructive-action safety:
  - `remove` confirmation by default and `--yes` bypass.
- Coverage and quality baseline:
  - `pytest`, `pytest-cov`, `ruff`, `pyrefly`.

### In Progress

- Consolidation migration assistant polish for mixed
  `.claude` / `.agents` / cross-tool setups.

## Milestone 2: Agent Coverage and Feature Parity

### Planned

- Expand agent registry from 4 to 40+ agents (GitHub Copilot, Gemini CLI,
  Windsurf, Cline, Aider, Augment, Roo Code, Amp, Kilo Code, Sourcegraph,
  OpenHands, etc.) to match the reference implementation.
- Add `init` command to scaffold new SKILL.md templates.
- Add `install` command to restore skills from project lock file.
- Add `--yes` and `--all` flags to `add` for non-interactive CI/CD usage.
- Support `metadata.internal: true` for experimental skills hidden behind
  `INSTALL_INTERNAL_SKILLS=1`.

## Milestone 3: Code Quality and Hardening

### Planned

- Fix operator precedence ambiguity in lock entry construction.
- Lazy evaluation for agent global_skills_dir (currently baked at import time).
- Extract duplicated `_copy_directory` into shared utility.
- Add git clone timeout to prevent hangs on slow/malicious repos.
- Reuse httpx clients for connection pooling in update checks.
- Add warning logs when lock files are silently replaced due to parse errors.
- Better migration guidance and summaries for conflict-heavy projects.
- CI pipeline with required quality and coverage gates.

## Milestone 4: Test Coverage

### Planned

- Raise `remove.py` coverage above 85% (currently 75%).
- Raise `source_parser.py` coverage above 85% (currently 73%).
- Raise `updates.py` coverage above 85% (currently 73%).
- Add optional integration test infrastructure with `@pytest.mark.integration`.
- Raise overall coverage target to 90%.

## Milestone 5: Ecosystem and Extensibility

### Planned

- Plugin manifest support (`.claude-plugin/marketplace.json`).
- `sync` command to discover skills from installed Python packages.
- Security audit integration before installation.
- Expanded docs and recipes for common setups.
- Consider relaxing `requires-python` from `>=3.13` to `>=3.11`.
