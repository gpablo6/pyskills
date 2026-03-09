"""Implementation for the ``remove`` command."""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from pyskills.services import (
    AGENTS,
    get_agent_base_dir,
    get_canonical_skills_dir,
    read_local_lock,
    remove_skill_agents_from_global_lock,
    remove_skill_from_global_lock,
    remove_skill_from_local_lock,
)
from pyskills.shared import sanitize_name


@click.command()
@click.argument("skills", nargs=-1)
@click.option("--agent", "agents", multiple=True, help="Agent target(s)")
@click.option(
    "--global",
    "global_install",
    is_flag=True,
    help="Remove globally installed skills",
)
@click.option(
    "--all",
    "remove_all",
    is_flag=True,
    help="Remove all tracked local or globally installed skills",
)
@click.option(
    "--yes",
    "assume_yes",
    is_flag=True,
    help="Skip confirmation prompt",
)
def remove(
    skills: tuple[str, ...],
    agents: tuple[str, ...],
    global_install: bool,
    remove_all: bool,
    assume_yes: bool,
) -> None:
    """Remove installed skills and update lock files.

    Parameters
    ----------
    skills : tuple of str
        Skill names to remove.
    agents : tuple of str
        Optional target agents to clean from.
    global_install : bool
        Whether to remove from global scope.
    remove_all : bool
        Whether to remove all skills for the selected scope.
    assume_yes : bool
        Whether to skip interactive confirmation.

    Returns
    -------
    None
        Writes removal output to stdout.
    """

    target_skills = _resolve_target_skills(
        skills=skills,
        global_install=global_install,
        remove_all=remove_all,
    )
    if not target_skills:
        raise click.ClickException(
            "No skills specified. Provide skill names or use --all."
        )

    target_agents = _resolve_target_agents(agents)
    if not assume_yes:
        _confirm_remove(
            target_skills=target_skills,
            target_agents=target_agents,
            global_install=global_install,
        )

    removed_count = 0
    for skill_name in target_skills:
        removed = _remove_skill_paths(
            skill_name=skill_name,
            target_agents=target_agents,
            global_install=global_install,
        )
        if removed:
            removed_count += 1
            click.echo(f"removed {skill_name}")
        else:
            click.echo(f"not found {skill_name}")

        if global_install:
            updated = remove_skill_agents_from_global_lock(
                skill_name,
                target_agents,
            )
            if not updated:
                remove_skill_from_global_lock(skill_name)
        else:
            remove_skill_from_local_lock(skill_name, cwd=Path.cwd())

    click.echo(f"done: removed {removed_count} skill(s)")


def _confirm_remove(
    *,
    target_skills: list[str],
    target_agents: list[str],
    global_install: bool,
) -> None:
    """Prompt user confirmation for remove operations."""

    scope = "global" if global_install else "project"
    sample = ", ".join(target_skills[:5])
    if len(target_skills) > 5:
        sample = f"{sample}, ..."
    message = (
        f"Remove {len(target_skills)} skill(s) from {scope} scope "
        f"for {len(target_agents)} agent(s)? [{sample}]"
    )
    proceed = click.confirm(message, default=False)
    if not proceed:
        click.echo("Remove aborted.")
        raise click.exceptions.Exit(0)


def _resolve_target_agents(agents: tuple[str, ...]) -> list[str]:
    """Resolve and validate target agent identifiers."""

    target_agents = list(agents) if agents else list(AGENTS.keys())
    invalid = [agent for agent in target_agents if agent not in AGENTS]
    if invalid:
        invalid_list = ", ".join(invalid)
        raise click.ClickException(f"Invalid agent(s): {invalid_list}")
    return target_agents


def _resolve_target_skills(
    *,
    skills: tuple[str, ...],
    global_install: bool,
    remove_all: bool,
) -> list[str]:
    """Resolve target skills from arguments or lock files."""

    if remove_all:
        if global_install:
            return sorted(_scan_installed_skills(global_install=True))
        local_lock = read_local_lock(cwd=Path.cwd())
        if local_lock.skills:
            return sorted(local_lock.skills.keys())
        return sorted(_scan_installed_skills(global_install=False))

    return list(skills)


def _scan_installed_skills(*, global_install: bool) -> set[str]:
    """Scan known install directories and return discovered skill names."""

    names: set[str] = set()
    canonical = get_canonical_skills_dir(global_install, cwd=Path.cwd())
    names.update(_read_skill_dir_names(canonical))

    for agent in AGENTS:
        try:
            base = get_agent_base_dir(
                agent,
                global_install,
                cwd=Path.cwd(),
            )
        except ValueError:
            continue
        names.update(_read_skill_dir_names(base))

    return names


def _read_skill_dir_names(base_dir: Path) -> set[str]:
    """Read direct child directory names from ``base_dir``."""

    if not base_dir.exists():
        return set()
    return {
        child.name
        for child in base_dir.iterdir()
        if child.is_dir() or child.is_symlink()
    }


def _remove_skill_paths(
    *,
    skill_name: str,
    target_agents: list[str],
    global_install: bool,
) -> bool:
    """Remove all known install paths for a skill.

    Returns ``True`` when at least one path was removed.
    """

    sanitized = sanitize_name(skill_name)
    removed = False

    paths: set[Path] = set()
    canonical = (
        get_canonical_skills_dir(global_install, cwd=Path.cwd()) / sanitized
    )
    paths.add(canonical)

    for agent in target_agents:
        try:
            agent_base = get_agent_base_dir(
                agent,
                global_install,
                cwd=Path.cwd(),
            )
        except ValueError:
            continue
        paths.add(agent_base / sanitized)

    for path in paths:
        if not (path.exists() or path.is_symlink()):
            continue
        shutil.rmtree(path, ignore_errors=True)
        removed = True

    return removed
