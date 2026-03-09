# Testing

## Tooling

- `pytest`: test runner.
- `pytest-cov`: coverage reports.
- `ruff`: linting.
- `pyrefly`: static type checking.

## Commands

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/pyrefly check
```

Coverage reporting is configured in `pyproject.toml` and runs with
`pytest` by default.

## Test Layout

- `tests/cli/`: command behavior, output, wiring, and flows.
- `tests/services/`: pure logic and orchestration.
- `tests/models/`: model import and schema-level checks.

## Strategy

- Keep CLI tests focused on user-facing behavior and command wiring.
- Keep core logic tests at service level.
- Prefer deterministic tests:
  - use isolated filesystems,
  - monkeypatch network/process boundaries,
  - avoid external network access in tests.

## High-Risk Areas

Prioritize test coverage for:

- filesystem mutations (`add`, `remove`, `adopt` apply/undo),
- lockfile migrations and updates,
- source parsing and path sanitization,
- update checks across source types.

## Coverage Baseline

Current baseline target for the project is at least `85%` total
coverage. Raise this target as confidence grows.

## Known Coverage Gaps

Modules below baseline that should be prioritized:

- `cli/commands/remove.py` (75%): confirmation prompts, multi-agent cleanup.
- `services/source_parser.py` (73%): GitLab prefix, Windows paths, well-known
  skill filter.
- `services/updates.py` (73%): well-known and local update check paths.

## Integration Tests

All HTTP calls (httpx, GitHub API) are currently mocked. When real-endpoint
testing is needed, gate tests behind a `@pytest.mark.integration` marker
and skip by default.
