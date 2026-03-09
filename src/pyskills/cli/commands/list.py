"""Implementation for the ``list`` command."""

from __future__ import annotations

from pathlib import Path

import click

from pyskills.services import AGENTS, InstalledSkillInfo, list_installed_skills


@click.command(name="list")
@click.option(
    "--global",
    "global_install",
    is_flag=True,
    help="List globally installed skills",
)
@click.option("--agent", "agents", multiple=True, help="Filter by agent(s)")
def list_command(global_install: bool, agents: tuple[str, ...]) -> None:
    """List installed skills for a scope.

    Parameters
    ----------
    global_install : bool
        Whether to list global skills.
    agents : tuple of str
        Optional list of agents to filter attribution.

    Returns
    -------
    None
        Writes list output to stdout.
    """

    invalid_agents = [agent for agent in agents if agent not in AGENTS]
    if invalid_agents:
        values = ", ".join(invalid_agents)
        raise click.ClickException(f"Invalid agent(s): {values}")

    installed = list_installed_skills(
        global_install=global_install,
        cwd=Path.cwd(),
        agent_filter=list(agents) if agents else None,
    )

    scope_name = "Global" if global_install else "Project"
    if not installed:
        click.echo(f"No {scope_name.lower()} skills found.")
        return

    click.echo(f"{scope_name} skills")
    grouped = _group_skills(installed)
    for group_name in sorted(grouped.keys(), key=str.lower):
        click.echo("")
        click.echo(group_name)
        for skill in grouped[group_name]:
            path = _shorten_path(skill.path, Path.cwd())
            click.echo(f"- {skill.name} ({path})")
            click.echo(f"  {skill.description}")
            if skill.source:
                click.echo(f"  Source: {skill.source}")

            if skill.agents:
                names = [
                    AGENTS[name].display_name
                    for name in sorted(skill.agents)
                ]
                click.echo(f"  Agents: {', '.join(names)}")
            else:
                click.echo("  Agents: not linked")


def _shorten_path(path: Path, cwd: Path) -> str:
    """Shorten path output by replacing cwd and home prefixes."""

    home = Path.home()
    resolved = path.resolve()

    if resolved == home or home in resolved.parents:
        return f"~/{resolved.relative_to(home).as_posix()}"

    if resolved == cwd or cwd in resolved.parents:
        return f"./{resolved.relative_to(cwd).as_posix()}"

    return resolved.as_posix()


def _group_skills(
    installed: list[InstalledSkillInfo],
) -> dict[str, list[InstalledSkillInfo]]:
    """Group installed skills by plugin name or source."""

    grouped: dict[str, list] = {}
    for skill in installed:
        group = _group_name(skill.plugin_name, skill.source)
        grouped.setdefault(group, []).append(skill)
    return grouped


def _group_name(plugin_name: str | None, source: str | None) -> str:
    """Build a user-facing group header."""

    if plugin_name:
        title = " ".join(
            token.capitalize()
            for token in plugin_name.split("-")
            if token
        )
        return title or "General"

    if source:
        return f"Source: {source}"

    return "General"
