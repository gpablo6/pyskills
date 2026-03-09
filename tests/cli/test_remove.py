import json
import importlib
from pathlib import Path

from click.testing import CliRunner

from pyskills.cli import cli


def test_remove_project_skill_updates_local_lock() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        source_dir = Path("source") / "demo"
        source_dir.mkdir(parents=True)
        (source_dir / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\n",
            encoding="utf-8",
        )

        add_result = runner.invoke(
            cli,
            [
                "add",
                "./source",
                "--agent",
                "codex",
                "--copy",
            ],
        )
        assert add_result.exit_code == 0

        install_path = Path(".agents/skills/demo")
        assert install_path.exists()

        lock_before = json.loads(
            Path("skills-lock.json").read_text(encoding="utf-8")
        )
        assert "demo" in lock_before["skills"]

        remove_result = runner.invoke(
            cli,
            ["remove", "demo", "--agent", "codex", "--yes"],
        )
        assert remove_result.exit_code == 0

        assert not install_path.exists()

        lock_after = json.loads(
            Path("skills-lock.json").read_text(encoding="utf-8")
        )
        assert "demo" not in lock_after["skills"]


def test_remove_all_uses_local_lock_entries() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        source_dir = Path("source") / "demo"
        source_dir.mkdir(parents=True)
        (source_dir / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\n",
            encoding="utf-8",
        )

        add_result = runner.invoke(
            cli,
            [
                "add",
                "./source",
                "--agent",
                "codex",
                "--copy",
            ],
        )
        assert add_result.exit_code == 0

        remove_result = runner.invoke(
            cli,
            ["remove", "--all", "--agent", "codex", "--yes"],
        )
        assert remove_result.exit_code == 0
        assert "removed demo" in remove_result.output


def test_remove_aborts_without_confirmation() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        source_dir = Path("source") / "demo"
        source_dir.mkdir(parents=True)
        (source_dir / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\n",
            encoding="utf-8",
        )
        add_result = runner.invoke(
            cli,
            ["add", "./source", "--agent", "codex", "--copy"],
        )
        assert add_result.exit_code == 0

        remove_result = runner.invoke(
            cli,
            ["remove", "demo", "--agent", "codex"],
            input="n\n",
        )

        assert remove_result.exit_code == 0
        assert "Remove aborted." in remove_result.output
        assert (Path(".agents/skills/demo")).exists()


def test_remove_invalid_agent_fails() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["remove", "demo", "--agent", "bad"])
    assert result.exit_code != 0
    assert "Invalid agent(s): bad" in result.output


def test_remove_target_resolution_helpers(monkeypatch) -> None:
    remove_module = importlib.import_module("pyskills.cli.commands.remove")

    class Lock:
        skills = {"demo": object()}

    monkeypatch.setattr(remove_module, "read_local_lock", lambda cwd: Lock())
    result = remove_module._resolve_target_skills(
        skills=(),
        global_install=False,
        remove_all=True,
    )
    assert result == ["demo"]

    monkeypatch.setattr(
        remove_module,
        "_scan_installed_skills",
        lambda global_install: {"a", "b"},  # noqa: ARG005
    )
    global_result = remove_module._resolve_target_skills(
        skills=(),
        global_install=True,
        remove_all=True,
    )
    assert global_result == ["a", "b"]
