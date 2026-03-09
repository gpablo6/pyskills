import importlib

from click.testing import CliRunner

from pyskills.cli import cli
from pyskills.cli.commands.find import _choose_result, _format_installs
from pyskills.services.find import SearchSkill


def test_find_requires_query() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["find"])

    assert result.exit_code == 0
    assert "Usage: pyskills find <query>" in result.output


def test_find_prints_results(monkeypatch) -> None:
    find_module = importlib.import_module("pyskills.cli.commands.find")

    def fake_search(query: str, limit: int = 10):  # noqa: ANN001, ANN202
        assert query == "review"
        assert limit == 10
        return [
            type(
                "SearchSkill",
                (),
                {
                    "name": "Find Skills",
                    "slug": "find-skills",
                    "source": "vercel-labs/skills",
                    "installs": 1450,
                },
            )()
        ]

    monkeypatch.setattr(
        find_module,
        "search_skills_api",
        fake_search,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["find", "review"])

    assert result.exit_code == 0
    assert "Found 1 result(s):" in result.output
    assert "Add: pyskills add vercel-labs/skills@find-skills" in result.output


def test_find_install_selected_calls_add(monkeypatch) -> None:
    find_module = importlib.import_module("pyskills.cli.commands.find")

    def fake_search(query: str, limit: int = 10):  # noqa: ANN001, ANN202
        assert query == "review"
        assert limit == 10
        return [
            type(
                "SearchSkill",
                (),
                {
                    "name": "Find Skills",
                    "slug": "find-skills",
                    "source": "vercel-labs/skills",
                    "installs": 1450,
                },
            )()
        ]

    add_calls = []

    def fake_add(**kwargs):  # noqa: ANN003, ANN201
        add_calls.append(kwargs)

    monkeypatch.setattr(find_module, "search_skills_api", fake_search)
    monkeypatch.setattr(find_module.add_command, "callback", fake_add)

    runner = CliRunner()
    result = runner.invoke(cli, ["find", "review", "--install"])

    assert result.exit_code == 0
    assert add_calls
    assert add_calls[0]["source"] == "vercel-labs/skills@find-skills"


def test_format_installs_helpers() -> None:
    assert _format_installs(0) == ""
    assert _format_installs(999) == "999"
    assert _format_installs(1_500) == "1.5K"
    assert _format_installs(2_000_000) == "2M"


def test_choose_result_helper(monkeypatch) -> None:
    items = [
        SearchSkill(
            name="A",
            slug="a",
            source="x",
            installs=1,
        ),
        SearchSkill(
            name="B",
            slug="b",
            source="x",
            installs=2,
        ),
    ]

    monkeypatch.setattr("click.prompt", lambda *args, **kwargs: 2)
    selected = _choose_result(items)
    assert selected is not None
    assert selected.name == "B"


def test_choose_result_cancel(monkeypatch) -> None:
    items = [
        SearchSkill(name="A", slug="a", source="x", installs=1),
        SearchSkill(name="B", slug="b", source="x", installs=2),
    ]
    monkeypatch.setattr("click.prompt", lambda *args, **kwargs: 0)
    assert _choose_result(items) is None
