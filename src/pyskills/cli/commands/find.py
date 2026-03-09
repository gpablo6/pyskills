"""Implementation for the ``find`` command."""

from __future__ import annotations

import click

from pyskills.services import SearchSkill, search_skills_api
from .add import add as add_command


@click.command()
@click.argument("query", nargs=-1)
@click.option(
    "--limit",
    type=int,
    default=10,
    show_default=True,
    help="Maximum number of results",
)
@click.option(
    "--install",
    "install_selected",
    is_flag=True,
    help="Prompt to install one result",
)
def find(
    query: tuple[str, ...],
    limit: int,
    install_selected: bool,
) -> None:
    """Search for skills and print install-ready suggestions.

    Parameters
    ----------
    query : tuple of str
        Query terms.

    Returns
    -------
    None
        Writes search results to stdout.
    """

    search_query = " ".join(query).strip()
    if not search_query and click.get_text_stream("stdin").isatty():
        search_query = click.prompt("Search query").strip()

    if not search_query:
        click.echo("Usage: pyskills find <query>")
        click.echo("Example: pyskills find review")
        return

    results = search_skills_api(search_query, limit=limit)
    if not results:
        click.echo("No skills found.")
        return

    click.echo(f"Found {len(results)} result(s):")
    for idx, skill in enumerate(results, start=1):
        installs = _format_installs(skill.installs)
        source = skill.source or "(unknown source)"
        click.echo(f"{idx}. {skill.name}")
        click.echo(f"  Source: {source}")
        if installs:
            click.echo(f"  Installs: {installs}")
        if skill.source:
            click.echo(f"  Add: pyskills add {skill.source}@{skill.slug}")

    if not install_selected:
        return

    callback = add_command.callback
    if callback is None:
        raise click.ClickException("add callback is not available")

    selected = _choose_result(results)
    if selected is None:
        click.echo("Install cancelled.")
        return
    if not selected.source:
        raise click.ClickException("Selected result has no installable source")

    callback(  # type: ignore[misc]
        source=f"{selected.source}@{selected.slug}",
        skills=(),
        agents=(),
        global_install=False,
        copy_mode=False,
        list_only=False,
    )


def _format_installs(installs: int) -> str:
    """Format installs counts for compact display."""

    if installs <= 0:
        return ""
    if installs >= 1_000_000:
        value = installs / 1_000_000
        return f"{value:.1f}".rstrip("0").rstrip(".") + "M"
    if installs >= 1_000:
        value = installs / 1_000
        return f"{value:.1f}".rstrip("0").rstrip(".") + "K"
    return str(installs)


def _choose_result(results: list[SearchSkill]) -> SearchSkill | None:
    """Prompt user to select one result from numbered output."""

    if len(results) == 1:
        return results[0]

    max_index = len(results)
    choice = click.prompt(
        f"Install which result? [1-{max_index}] (0 to cancel)",
        type=int,
        default=1,
    )
    if choice == 0:
        return None
    if choice < 1 or choice > max_index:
        raise click.ClickException("Invalid selection")
    return results[choice - 1]
