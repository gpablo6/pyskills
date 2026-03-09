# Maintainer Guide

## Development Environment

- Python from local `.venv`.
- Dependency management through `uv`.
- Runtime entrypoint:
  - `PYTHONPATH=src .venv/bin/python -m pyskills`

## Contributor Workflow

When implementing a feature:

1. Update/add models and contracts.
2. Implement service logic.
3. Wire CLI behavior.
4. Add or update tests.
5. Update docs and docstrings.

## Documentation Standards

- Use Numpydoc style for modules, classes, and public functions.
- Keep behavior docs and command help text aligned.
- Keep user-facing guidance in `README.md`.
- Keep maintainer/deep technical docs in `docs/`.

## Code Organization Rules

- Keep business logic out of CLI commands.
- Keep modules focused and composable.
- Use `pydantic` models for typed boundaries.
- Keep shared utilities in `pyskills.shared`.

## Quality Gates

All must pass before merge:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/pyrefly check
```

## Operational Safety

- Validate and sanitize user-provided paths.
- Favor confirmation for destructive actions.
- Preserve deterministic lockfile writes.
- Use backup-first patterns for migration-style changes.
