import json
from pathlib import Path

from click.testing import CliRunner

from pyskills.cli import cli


def test_add_project_install_updates_local_lock() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        source_dir = Path("source") / "demo"
        source_dir.mkdir(parents=True)
        (source_dir / "SKILL.md").write_text(
            "---\nname: demo\ndescription: local demo\n---\n",
            encoding="utf-8",
        )

        result = runner.invoke(
            cli,
                [
                    "add",
                    "./source",
                    "--agent",
                    "codex",
                    "--copy",
                ],
        )

        assert result.exit_code == 0

        lock_path = Path("skills-lock.json")
        assert lock_path.exists()

        lock_data = json.loads(lock_path.read_text(encoding="utf-8"))
        assert lock_data["version"] == 1
        assert "demo" in lock_data["skills"]
        assert lock_data["skills"]["demo"]["source_type"] == "local"
        assert lock_data["skills"]["demo"]["computed_hash"]
