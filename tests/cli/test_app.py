from click.testing import CliRunner

from pyskills.cli import cli


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Manage agent skills" in result.output
