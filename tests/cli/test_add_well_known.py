from pathlib import Path
import importlib

from click.testing import CliRunner

from pyskills.cli import cli
from pyskills.models import ParsedSource, SourceType


def test_add_well_known_source(monkeypatch, tmp_path: Path) -> None:
    add_module = importlib.import_module("pyskills.cli.commands.add")

    source_dir = tmp_path / "wk" / "demo"
    source_dir.mkdir(parents=True)
    (source_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: demo\n---\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        add_module,
        "parse_source",
        lambda _: ParsedSource(
            type=SourceType.WELL_KNOWN,
            url="https://example.com",
        ),
    )
    monkeypatch.setattr(
        add_module,
        "materialize_well_known_source",
        lambda url, skill_filter=None: tmp_path / "wk",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "add",
            "https://example.com",
            "--agent",
            "codex",
            "--copy",
        ],
    )

    assert result.exit_code == 0
    assert "installed demo -> codex" in result.output
