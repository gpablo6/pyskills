"""Implementation for the ``update`` command."""

from __future__ import annotations

import click

from pyskills.services import (
    build_update_install_url,
    check_global_updates,
    list_installed_skills,
    read_global_lock,
)

from .add import add as add_command


@click.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be updated without reinstalling",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Include detailed skip reasons for unsupported sources",
)
def update(dry_run: bool, verbose: bool) -> None:
    """Update globally tracked skills with available updates."""

    outdated, skipped = check_global_updates(verbose=verbose)
    if not outdated:
        click.echo("All tracked skills are up to date.")
        if verbose and skipped:
            click.echo("")
            click.echo(f"Skipped {len(skipped)} skill(s):")
            for item in skipped:
                click.echo(f"- {item.name}: {item.reason}")
        return

    callback = add_command.callback
    if callback is None:
        raise click.ClickException("add callback is not available")

    installed = list_installed_skills(global_install=True)
    agents_by_skill = {skill.name: sorted(skill.agents) for skill in installed}
    lock = read_global_lock()
    for name, entry in lock.skills.items():
        if entry.agents:
            agents_by_skill[name] = sorted(entry.agents)

    success = 0
    fail = 0

    for item in outdated:
        install_url = build_update_install_url(item.entry)
        target_agents = tuple(agents_by_skill.get(item.name, []))
        use_copy_mode = item.entry.install_mode == "copy"
        if dry_run:
            click.echo(
                f"Would update {item.name} from {install_url} "
                f"for agents: {', '.join(target_agents) or '(auto)'}"
            )
            success += 1
            continue

        click.echo(f"Updating {item.name}...")
        try:
            callback(  # type: ignore[misc]
                source=install_url,
                skills=(item.name,),
                agents=target_agents,
                global_install=True,
                copy_mode=use_copy_mode,
                list_only=False,
            )
            success += 1
        except Exception as exc:  # noqa: BLE001
            fail += 1
            click.echo(f"failed {item.name}: {exc}")

    action = "Planned" if dry_run else "Updated"
    click.echo(f"{action} {success} skill(s), failed {fail}.")

    if verbose and skipped:
        click.echo("")
        click.echo(f"Skipped {len(skipped)} skill(s):")
        for item in skipped:
            click.echo(f"- {item.name}: {item.reason}")
