from pathlib import Path
import importlib

from click.testing import CliRunner

from pyskills.cli import cli
from pyskills.models import ParsedSource, SourceType


def test_add_remote_source_uses_clone(monkeypatch, tmp_path: Path) -> None:
    add_module = importlib.import_module("pyskills.cli.commands.add")
    repo_dir = tmp_path / "cloned"
    skill_dir = repo_dir / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: test\n---\n",
        encoding="utf-8",
    )

    def fake_parse_source(_: str) -> ParsedSource:
        return ParsedSource(
            type=SourceType.GITHUB,
            url="https://github.com/acme/skills.git",
        )

    def fake_clone_repo(url: str, ref: str | None = None) -> Path:
        assert "github.com/acme/skills.git" in url
        assert ref is None
        return repo_dir

    monkeypatch.setattr(add_module, "parse_source", fake_parse_source)
    monkeypatch.setattr(add_module, "clone_repo", fake_clone_repo)

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "add",
                "acme/skills",
                "--agent",
                "codex",
                "--copy",
            ],
        )

    assert result.exit_code == 0
    assert "installed demo -> codex" in result.output


def test_add_rejects_unknown_skill_name(monkeypatch, tmp_path: Path) -> None:
    add_module = importlib.import_module("pyskills.cli.commands.add")
    skill_dir = tmp_path / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: test\n---\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        add_module,
        "parse_source",
        lambda _: ParsedSource(
            type=SourceType.LOCAL,
            url=str(tmp_path),
            local_path=tmp_path,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "add",
            str(tmp_path),
            "--agent",
            "codex",
            "--skill",
            "missing",
        ],
    )

    assert result.exit_code != 0
    assert "No matching skills found" in result.output


def test_add_list_only_outputs_discovered_skills(tmp_path: Path) -> None:
    runner = CliRunner()

    source = tmp_path / "source"
    demo = source / "demo"
    demo.mkdir(parents=True)
    (demo / "SKILL.md").write_text(
        "---\nname: demo\ndescription: demo desc\n---\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli, ["add", str(source), "--list"])

    assert result.exit_code == 0
    assert "demo: demo desc" in result.output


def test_add_invalid_agent_fails(tmp_path: Path) -> None:
    runner = CliRunner()
    source = tmp_path / "source"
    demo = source / "demo"
    demo.mkdir(parents=True)
    (demo / "SKILL.md").write_text(
        "---\nname: demo\ndescription: demo\n---\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        cli,
        ["add", str(source), "--agent", "nonexistent"],
    )

    assert result.exit_code != 0
    assert "Invalid agent: nonexistent" in result.output
