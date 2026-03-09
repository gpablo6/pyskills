"""Implementation for the ``check`` command."""

from __future__ import annotations

import click

from pyskills.services import check_global_updates, read_global_lock


@click.command()
@click.option(
    "--verbose",
    is_flag=True,
    help="Include detailed skip reasons for unsupported sources",
)
def check(verbose: bool) -> None:
    """Check globally tracked skills for available updates."""

    lock = read_global_lock()
    if not lock.skills:
        click.echo("No globally tracked skills found.")
        return

    outdated, skipped = check_global_updates(verbose=verbose)

    if not outdated:
        click.echo("All tracked skills are up to date.")
    else:
        click.echo(f"{len(outdated)} update(s) available:")
        for item in outdated:
            click.echo(f"- {item.name}")

    if skipped:
        click.echo("")
        click.echo(f"Skipped {len(skipped)} skill(s):")
        for item in skipped:
            click.echo(f"- {item.name}: {item.reason}")
