# AGENTS.md

## Purpose

This file defines repository-level coding and collaboration rules for contributors and coding agents.

## Architecture Rules

- Keep a layered design:
  - `pyskills.models` for Pydantic domain models only.
  - `pyskills.services` for business logic and orchestration.
  - `pyskills.cli` for Click command definitions and CLI composition.
  - `pyskills.shared` for common constants and utility helpers.
- Avoid putting business logic inside CLI command functions.
- Prefer small, focused modules over monolithic files.

## Documentation Rules

- Use Numpydoc style docstrings:
  - https://numpydoc.readthedocs.io/en/latest/format.html
- Add docstrings to:
  - public modules
  - public classes
  - public functions
- Include `Parameters`, `Returns`, and `Raises` where relevant.
- Keep documentation aligned with behavior; update docstrings in the same change as code.

## Quality Gates

All of the following must pass before finalizing work:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/pyrefly check
```

## Testing Rules

- Mirror runtime package structure in tests:
  - `tests/cli`
  - `tests/services`
  - `tests/models`
- Add or update tests for every behavior change.
- Prefer service-level tests for logic and keep CLI tests focused on wiring/output.

## Model and Typing Rules

- Use Pydantic models for external/stateful boundaries.
- Keep model definitions grouped by concern under `pyskills/models`.
- Prefer explicit typing (`Literal`, concrete return types, typed collections).

## Safety Rules

- Validate and sanitize filesystem paths to prevent traversal issues.
- Sanitize user-provided names before using them as directory names.
- Preserve deterministic behavior in lockfile writing and hashing.

## Change Management

When implementing a new feature, follow this sequence:
1. Update models and contracts.
2. Implement service logic.
3. Wire CLI behavior.
4. Add/adjust tests.
5. Update `README.md` and docstrings as needed.
