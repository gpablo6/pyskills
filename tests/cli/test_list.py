from click.testing import CliRunner

from pyskills.cli import cli


def test_list_shows_project_skills() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        from pathlib import Path

        source = Path("source") / "demo"
        source.mkdir(parents=True, exist_ok=True)
        (source / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\n",
            encoding="utf-8",
        )

        create = runner.invoke(
            cli,
            [
                "add",
                "./source",
                "--agent",
                "codex",
                "--copy",
            ],
        )

        assert create.exit_code == 0

        listed = runner.invoke(cli, ["list"])
        assert listed.exit_code == 0
        assert "Project skills" in listed.output
        assert "demo" in listed.output
        assert "Source:" in listed.output
        assert "Codex" in listed.output


def test_list_with_invalid_agent_fails() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--agent", "unknown-agent"])

    assert result.exit_code != 0
    assert "Invalid agent(s)" in result.output


def test_list_global_empty_scope() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["list", "--global"])

    assert result.exit_code == 0
    assert "No global skills found." in result.output
