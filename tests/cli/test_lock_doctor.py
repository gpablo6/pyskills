import json
from pathlib import Path

from click.testing import CliRunner

from pyskills.cli import cli


def test_lock_doctor_reports_missing_locks(monkeypatch) -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        monkeypatch.setenv("HOME", str(Path.cwd()))

        result = runner.invoke(cli, ["lock-doctor"])

    assert result.exit_code == 0
    assert "Global lock" in result.output
    assert "Local lock" in result.output
    assert "Warning:" in result.output


def test_lock_doctor_reports_outdated_global_version(monkeypatch) -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        monkeypatch.setenv("HOME", str(Path.cwd()))

        global_dir = Path.home() / ".agents"
        global_dir.mkdir(parents=True, exist_ok=True)
        (global_dir / ".skill-lock.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "skills": {
                        "demo": {
                            "source": "https://github.com/acme/repo.git",
                            "source_type": "github",
                            "source_url": "https://github.com/acme/repo.git",
                            "skill_path": "skills/demo/SKILL.md",
                            "skill_folder_hash": "abc",
                            "installed_at": "2026-01-01T00:00:00Z",
                            "updated_at": "2026-01-01T00:00:00Z",
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        result = runner.invoke(cli, ["lock-doctor"])

    assert result.exit_code == 0
    assert "outdated" in result.output.lower()
    assert "missing source_id" in result.output.lower()
