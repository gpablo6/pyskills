from pathlib import Path

from click.testing import CliRunner

from pyskills.cli import cli


def test_adopt_dry_run_output() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        skill_dir = Path(".claude/skills/demo")
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\n",
            encoding="utf-8",
        )

        result = runner.invoke(cli, ["adopt"])

    assert result.exit_code == 0
    assert "Adopt dry-run" in result.output
    assert "demo" in result.output
    assert "Dry-run only" in result.output


def test_adopt_apply_output() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        skill_dir = Path(".claude/skills/demo")
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\n",
            encoding="utf-8",
        )

        result = runner.invoke(cli, ["adopt", "--apply", "--yes"])

    assert result.exit_code == 0
    assert "Adopt apply" in result.output
    assert "Apply complete." in result.output
    assert "Backups created:" in result.output
    assert "Manifest:" in result.output


def test_adopt_apply_prompt_abort() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        skill_dir = Path(".claude/skills/demo")
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\n",
            encoding="utf-8",
        )

        result = runner.invoke(cli, ["adopt", "--apply"], input="n\n")

    assert result.exit_code == 0
    assert "Adopt apply aborted." in result.output


def test_adopt_dry_run_skill_filter() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        demo = Path(".claude/skills/demo")
        demo.mkdir(parents=True)
        (demo / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\n",
            encoding="utf-8",
        )
        alpha = Path(".claude/skills/alpha")
        alpha.mkdir(parents=True)
        (alpha / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: alpha\n---\n",
            encoding="utf-8",
        )

        result = runner.invoke(cli, ["adopt", "--skill", "demo"])

    assert result.exit_code == 0
    assert "Total skills: 1" in result.output
    assert "demo" in result.output
    assert "alpha" not in result.output


def test_adopt_filter_unknown_skill_fails() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["adopt", "--skill", "missing"])

    assert result.exit_code != 0
    assert "Unknown skill target(s): missing" in result.output


def test_adopt_apply_interactive_select_single_skill() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        demo = Path(".claude/skills/demo")
        demo.mkdir(parents=True)
        (demo / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\n",
            encoding="utf-8",
        )
        alpha = Path(".claude/skills/alpha")
        alpha.mkdir(parents=True)
        (alpha / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: alpha\n---\n",
            encoding="utf-8",
        )

        result = runner.invoke(
            cli,
            ["adopt", "--apply"],
            input="y\n2\n",
        )

        assert (Path(".agents/skills/demo")).exists()
        assert not (Path(".agents/skills/alpha")).exists()

    assert result.exit_code == 0
    assert "Target filter: demo" in result.output


def test_adopt_apply_interactive_cancel() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        demo = Path(".claude/skills/demo")
        demo.mkdir(parents=True)
        (demo / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\n",
            encoding="utf-8",
        )

        result = runner.invoke(
            cli,
            ["adopt", "--apply"],
            input="y\n0\n",
        )

        assert not (Path(".agents/skills/demo")).exists()

    assert result.exit_code == 0
    assert "Adopt apply aborted (no skills selected)." in result.output


def test_adopt_undo_from_manifest() -> None:
    runner = CliRunner()

    with runner.isolated_filesystem():
        demo = Path(".claude/skills/demo")
        demo.mkdir(parents=True)
        (demo / "SKILL.md").write_text(
            "---\nname: demo\ndescription: demo\n---\nbody\n",
            encoding="utf-8",
        )

        apply_result = runner.invoke(
            cli,
            ["adopt", "--apply", "--yes"],
        )
        assert apply_result.exit_code == 0

        manifest = ""
        for line in apply_result.output.splitlines():
            if line.startswith("Manifest: "):
                manifest = line.split("Manifest: ", 1)[1].strip()
                break
        assert manifest

        undo_result = runner.invoke(cli, ["adopt", "--undo", manifest])
        assert undo_result.exit_code == 0
        assert "Adopt undo" in undo_result.output
        assert (Path(".claude/skills/demo/SKILL.md")).exists()
