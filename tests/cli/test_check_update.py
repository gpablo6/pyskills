import importlib
from pathlib import Path

from click.testing import CliRunner

from pyskills.cli import cli
from pyskills.models import SkillLockEntry, SkillLockFile
from pyskills.services.listing import InstalledSkillInfo
from pyskills.services.updates import OutdatedSkill


def test_check_no_global_skills(monkeypatch) -> None:
    check_module = importlib.import_module("pyskills.cli.commands.check")

    class Lock:
        skills = {}

    monkeypatch.setattr(check_module, "read_global_lock", lambda: Lock())

    runner = CliRunner()
    result = runner.invoke(cli, ["check"])

    assert result.exit_code == 0
    assert "No globally tracked skills found." in result.output


def test_update_invokes_add_callback(monkeypatch) -> None:
    update_module = importlib.import_module("pyskills.cli.commands.update")

    entry = SkillLockEntry(
        source="https://github.com/acme/repo.git",
        source_type="github",
        source_url="https://github.com/acme/repo.git",
        skill_path="skills/demo/SKILL.md",
        skill_folder_hash="old",
        installed_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        agents=["codex"],
        install_mode="copy",
    )

    monkeypatch.setattr(
        update_module,
        "check_global_updates",
        lambda verbose=False: (  # noqa: ARG005
            [OutdatedSkill(name="demo", entry=entry, latest_hash="new")],
            [],
        ),
    )
    monkeypatch.setattr(
        update_module,
        "list_installed_skills",
        lambda global_install: [  # noqa: ARG005
            InstalledSkillInfo(
                name="demo",
                description="Demo",
                path=Path(".agents/skills/demo"),
                scope="global",
                agents={"codex", "claude-code"},
            )
        ],
    )
    monkeypatch.setattr(
        update_module,
        "read_global_lock",
        lambda: type("Lock", (), {"skills": {"demo": entry}})(),
    )

    calls = []

    def fake_add(**kwargs):  # noqa: ANN003, ANN201
        calls.append(kwargs)

    monkeypatch.setattr(update_module.add_command, "callback", fake_add)

    runner = CliRunner()
    result = runner.invoke(cli, ["update"])

    assert result.exit_code == 0
    assert calls
    assert calls[0]["global_install"] is True
    assert calls[0]["agents"] == ("codex",)
    assert calls[0]["copy_mode"] is True
    assert calls[0]["skills"] == ("demo",)
    assert "Updated 1 skill(s), failed 0." in result.output


def test_check_verbose_prints_skipped(monkeypatch) -> None:
    check_module = importlib.import_module("pyskills.cli.commands.check")

    lock = SkillLockFile(
        version=1,
        skills={
            "demo": SkillLockEntry(
                source="x",
                source_type="git",
                source_url="x",
                skill_path="skills/demo/SKILL.md",
                skill_folder_hash="hash",
                installed_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        },
    )

    monkeypatch.setattr(check_module, "read_global_lock", lambda: lock)
    monkeypatch.setattr(
        check_module,
        "check_global_updates",
        lambda verbose=False: (  # noqa: ARG005
            [],
            [type("Skipped", (), {"name": "demo", "reason": "Unsupported"})()],
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--verbose"])

    assert result.exit_code == 0
    assert "Skipped 1 skill(s):" in result.output


def test_update_dry_run_prints_plan_and_skipped(monkeypatch) -> None:
    update_module = importlib.import_module("pyskills.cli.commands.update")
    entry = SkillLockEntry(
        source="https://github.com/acme/repo.git",
        source_type="github",
        source_url="https://github.com/acme/repo.git",
        skill_path="skills/demo/SKILL.md",
        skill_folder_hash="old",
        installed_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        agents=["codex"],
        install_mode="symlink",
    )

    monkeypatch.setattr(
        update_module,
        "check_global_updates",
        lambda verbose=False: (  # noqa: ARG005
            [OutdatedSkill(name="demo", entry=entry, latest_hash="new")],
            [type("Skipped", (), {"name": "x", "reason": "Unsupported"})()],
        ),
    )
    monkeypatch.setattr(
        update_module,
        "list_installed_skills",
        lambda global_install: [],  # noqa: ARG005
    )
    monkeypatch.setattr(
        update_module,
        "read_global_lock",
        lambda: type("Lock", (), {"skills": {"demo": entry}})(),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["update", "--dry-run", "--verbose"])

    assert result.exit_code == 0
    assert "Would update demo" in result.output
    assert "Planned 1 skill(s), failed 0." in result.output
    assert "Skipped 1 skill(s):" in result.output


def test_update_reports_failure_from_add_callback(monkeypatch) -> None:
    update_module = importlib.import_module("pyskills.cli.commands.update")
    entry = SkillLockEntry(
        source="https://github.com/acme/repo.git",
        source_type="github",
        source_url="https://github.com/acme/repo.git",
        skill_path="skills/demo/SKILL.md",
        skill_folder_hash="old",
        installed_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        agents=["codex"],
        install_mode="copy",
    )

    monkeypatch.setattr(
        update_module,
        "check_global_updates",
        lambda verbose=False: (  # noqa: ARG005
            [OutdatedSkill(name="demo", entry=entry, latest_hash="new")],
            [],
        ),
    )
    monkeypatch.setattr(
        update_module,
        "list_installed_skills",
        lambda global_install: [],  # noqa: ARG005
    )
    monkeypatch.setattr(
        update_module,
        "read_global_lock",
        lambda: type("Lock", (), {"skills": {"demo": entry}})(),
    )

    def fake_add(**kwargs):  # noqa: ANN003, ANN201, ARG001
        raise RuntimeError("boom")

    monkeypatch.setattr(update_module.add_command, "callback", fake_add)

    runner = CliRunner()
    result = runner.invoke(cli, ["update"])

    assert result.exit_code == 0
    assert "failed demo: boom" in result.output
    assert "Updated 0 skill(s), failed 1." in result.output


def test_update_no_outdated_verbose_prints_skipped(monkeypatch) -> None:
    update_module = importlib.import_module("pyskills.cli.commands.update")

    monkeypatch.setattr(
        update_module,
        "check_global_updates",
        lambda verbose=False: (  # noqa: ARG005
            [],
            [type("Skipped", (), {"name": "x", "reason": "Unsupported"})()],
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["update", "--verbose"])

    assert result.exit_code == 0
    assert "All tracked skills are up to date." in result.output
    assert "Skipped 1 skill(s):" in result.output


def test_update_fails_when_add_callback_missing(monkeypatch) -> None:
    update_module = importlib.import_module("pyskills.cli.commands.update")
    entry = SkillLockEntry(
        source="https://github.com/acme/repo.git",
        source_type="github",
        source_url="https://github.com/acme/repo.git",
        skill_path="skills/demo/SKILL.md",
        skill_folder_hash="old",
        installed_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        agents=["codex"],
    )

    monkeypatch.setattr(
        update_module,
        "check_global_updates",
        lambda verbose=False: (  # noqa: ARG005
            [OutdatedSkill(name="demo", entry=entry, latest_hash="new")],
            [],
        ),
    )
    monkeypatch.setattr(update_module.add_command, "callback", None)

    runner = CliRunner()
    result = runner.invoke(cli, ["update"])

    assert result.exit_code != 0
    assert "add callback is not available" in result.output
