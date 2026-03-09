"""Implementation for the ``add`` command.

The command supports local sources, git-backed remote sources, and
well-known HTTP skill sources.
"""

from __future__ import annotations

from pathlib import Path

import click

from pyskills.models import (
    LocalSkillLockEntry,
    ParsedSource,
    Skill,
    SourceType,
)
from pyskills.services import (
    AGENTS,
    add_skill_to_global_lock,
    add_skill_to_local_lock,
    cleanup_temp_dir,
    clone_repo,
    compute_skill_folder_hash,
    detect_installed_agents,
    discover_skills,
    install_skill_for_agent,
    materialize_well_known_source,
    parse_source,
    parse_github_owner_repo,
    fetch_github_skill_folder_hash,
)
from pyskills.services.git import GitCloneError
from pyskills.services.well_known import WellKnownError


@click.command()
@click.argument("source")
@click.option(
    "--skill", "skills", multiple=True, help="Skill name(s) to install"
)
@click.option("--agent", "agents", multiple=True, help="Agent target(s)")
@click.option(
    "--global", "global_install", is_flag=True, help="Install globally"
)
@click.option(
    "--copy", "copy_mode", is_flag=True, help="Copy instead of symlink"
)
@click.option("--list", "list_only", is_flag=True, help="List skills only")
def add(
    source: str,
    skills: tuple[str, ...],
    agents: tuple[str, ...],
    global_install: bool,
    copy_mode: bool,
    list_only: bool,
) -> None:
    """Discover and install skills from a source.

    Parameters
    ----------
    source : str
        Source identifier for skills.
    skills : tuple of str
        Optional set of skill names to filter from discovery results.
    agents : tuple of str
        Optional target agents for installation. If omitted, detected
        installed agents are used.
    global_install : bool
        Whether to install in global agent directories.
    copy_mode : bool
        Whether to force copy mode instead of symlink mode.
    list_only : bool
        Whether to only list discovered skills without installing.

    Raises
    ------
    click.ClickException
        Raised when source parsing, clone/fetch, discovery, validation,
        or installation fails.

    Returns
    -------
    None
        Writes command output to stdout.
    """

    parsed = parse_source(source)
    temp_dir: Path | None = None

    try:
        skills_dir = _resolve_skills_dir(parsed)
        if parsed.type != SourceType.LOCAL:
            temp_dir = skills_dir

        selected_names = list(skills)
        if parsed.skill_filter and parsed.skill_filter not in selected_names:
            selected_names.append(parsed.skill_filter)

        discovered = discover_skills(skills_dir, parsed.subpath)
        if not discovered:
            raise click.ClickException("No skills found")

        selected = discovered
        if selected_names:
            wanted = {s.lower() for s in selected_names}
            selected = [s for s in discovered if s.name.lower() in wanted]
            if not selected:
                available = ", ".join(sorted({s.name for s in discovered}))
                raise click.ClickException(
                    "No matching skills found. "
                    f"Requested: {', '.join(selected_names)}. "
                    f"Available: {available}"
                )

        if list_only:
            for skill in selected:
                click.echo(f"{skill.name}: {skill.description}")
            return

        targets = list(agents) if agents else detect_installed_agents()
        if not targets:
            targets = ["codex"]

        for agent in targets:
            if agent not in AGENTS:
                raise click.ClickException(f"Invalid agent: {agent}")

        mode = "copy" if copy_mode else "symlink"

        for skill in selected:
            for agent in targets:
                result = install_skill_for_agent(
                    skill,
                    agent,
                    global_install=global_install,
                    mode=mode,
                )
                if result.success:
                    click.echo(
                        f"installed {skill.name} -> {agent} ({result.path})"
                    )
                else:
                    raise click.ClickException(
                        f"failed {skill.name} -> {agent}: {result.error}"
                    )

        _update_lock_entries(
            selected=selected,
            parsed=parsed,
            global_install=global_install,
            source_root=skills_dir,
            target_agents=targets,
            install_mode=mode,
        )
    finally:
        if temp_dir is not None:
            cleanup_temp_dir(temp_dir)


def _resolve_skills_dir(parsed: ParsedSource) -> Path:
    """Resolve the base directory where skills should be discovered.

    Parameters
    ----------
    parsed : ParsedSource
        Parsed source object.

    Returns
    -------
    pathlib.Path
        Directory used as discovery root.

    Raises
    ------
    click.ClickException
        Raised when source type is unsupported or clone/fetch fails.
    """

    if parsed.type == SourceType.LOCAL:
        return parsed.local_path or Path.cwd()

    if parsed.type == SourceType.WELL_KNOWN:
        try:
            return materialize_well_known_source(
                parsed.url,
                parsed.skill_filter,
            )
        except WellKnownError as exc:
            raise click.ClickException(str(exc)) from exc

    try:
        return clone_repo(parsed.url, parsed.ref)
    except GitCloneError as exc:
        raise click.ClickException(str(exc)) from exc


def _update_lock_entries(
    *,
    selected: list[Skill],
    parsed: ParsedSource,
    global_install: bool,
    source_root: Path,
    target_agents: list[str],
    install_mode: str,
) -> None:
    """Persist lock entries for successful installed skills.

    Parameters
    ----------
    selected : list of Skill
        Successfully selected skills for installation.
    parsed : ParsedSource
        Parsed source metadata.
    global_install : bool
        Whether install scope is global.
    source_root : pathlib.Path
        Root source directory used for discovery.
    target_agents : list of str
        Target agents used for installation.
    install_mode : str
        Install mode used for installation.

    Returns
    -------
    None
    """

    source_value = _lock_source_value(parsed)

    for skill in selected:
        folder_hash = compute_skill_folder_hash(skill.path)
        if global_install:
            skill_path = _skill_path_for_lock(skill.path, source_root)
            if parsed.type == SourceType.GITHUB and skill_path:
                owner_repo = parse_github_owner_repo(source_value)
                if owner_repo:
                    latest_hash = fetch_github_skill_folder_hash(
                        owner_repo,
                        skill_path,
                    )
                    if latest_hash:
                        folder_hash = latest_hash

            add_skill_to_global_lock(
                skill.name,
                source=source_value,
                source_type=parsed.type.value,
                source_url=source_value,
                skill_path=skill_path,
                skill_folder_hash=folder_hash,
                plugin_name=skill.plugin_name,
                source_id=_lock_source_id(parsed, source_value),
                agents=list(target_agents),
                install_mode=install_mode,
            )
            continue

        add_skill_to_local_lock(
            skill.name,
            LocalSkillLockEntry(
                source=source_value,
                source_type=parsed.type.value,
                computed_hash=folder_hash,
            ),
            cwd=Path.cwd(),
        )


def _lock_source_value(parsed: ParsedSource) -> str:
    """Resolve source identifier for lock entries."""

    if parsed.type == SourceType.LOCAL and parsed.local_path:
        return str(parsed.local_path)
    return parsed.url


def _lock_source_id(parsed: ParsedSource, source_value: str) -> str:
    """Build canonical lock source id for v2 global lock fidelity."""

    if parsed.type == SourceType.GITHUB:
        owner_repo = parse_github_owner_repo(source_value)
        if owner_repo:
            return owner_repo
        return source_value

    if parsed.type == SourceType.WELL_KNOWN:
        from urllib.parse import urlparse

        parsed_url = urlparse(source_value)
        host = parsed_url.hostname or "unknown"
        path = parsed_url.path.strip("/")
        return f"{host}/{path}" if path else host

    return source_value


def _skill_path_for_lock(skill_path: Path, source_root: Path) -> str:
    """Build lock path value for a skill's ``SKILL.md`` location."""

    resolved_skill = skill_path.resolve()
    resolved_root = source_root.resolve()

    if resolved_skill == resolved_root:
        return "SKILL.md"

    try:
        rel = resolved_skill.relative_to(resolved_root).as_posix()
    except ValueError:
        return "SKILL.md"
    return f"{rel}/SKILL.md"
