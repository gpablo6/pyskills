"""Implementation for the ``adopt`` command."""

from __future__ import annotations

from pathlib import Path

import click

from pyskills.services.adoption_manifest import undo_adoption
from pyskills.services.consolidation import (
    AdoptionItem,
    apply_adoption,
    build_adoption_report,
    filter_adoption_report,
)


@click.command()
@click.option(
    "--global",
    "global_install",
    is_flag=True,
    help="Scan global skill directories instead of project scope",
)
@click.option(
    "--skill",
    "skills",
    multiple=True,
    help="Limit migration to specific skill name(s)",
)
@click.option(
    "--apply",
    "apply_mode",
    is_flag=True,
    help="Apply the adoption plan and modify files",
)
@click.option(
    "--conflict",
    "conflict_policy",
    type=click.Choice(["keep-existing", "use-canonical"]),
    default="keep-existing",
    show_default=True,
    help="How to handle conflicting skill contents",
)
@click.option(
    "--yes",
    "assume_yes",
    is_flag=True,
    help="Skip confirmation prompt for --apply",
)
@click.option(
    "--undo",
    "undo_manifest",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="Undo an apply operation from a manifest file",
)
def adopt(
    global_install: bool,
    skills: tuple[str, ...],
    apply_mode: bool,
    conflict_policy: str,
    assume_yes: bool,
    undo_manifest: Path | None,
) -> None:
    """Run consolidation as dry-run or apply mode."""

    if undo_manifest and apply_mode:
        raise click.UsageError("Cannot use --undo and --apply together.")

    if undo_manifest:
        result = undo_adoption(manifest_path=undo_manifest)
        click.echo(f"Adopt undo ({undo_manifest})")
        click.echo("")
        click.echo(f"Restored paths: {result.restored_paths}")
        click.echo(
            f"Removed created paths: {result.removed_created_paths}"
        )
        click.echo(f"Skipped paths: {result.skipped_paths}")
        return

    selected_skills = list(skills) if skills else None

    if apply_mode:
        if not assume_yes:
            proceed = click.confirm(
                "Apply adoption changes to disk?",
                default=False,
            )
            if not proceed:
                click.echo("Adopt apply aborted.")
                return

        if not skills and not assume_yes:
            preview_report = build_adoption_report(
                global_install=global_install,
                cwd=Path.cwd(),
            )
            chosen = _prompt_apply_skill_selection(preview_report.items)
            if chosen is not None:
                if not chosen:
                    click.echo("Adopt apply aborted (no skills selected).")
                    return
                selected_skills = chosen

        try:
            report, apply_result = apply_adoption(
                global_install=global_install,
                cwd=Path.cwd(),
                conflict_policy=conflict_policy,
                skill_names=selected_skills,
            )
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
    else:
        report = build_adoption_report(
            global_install=global_install,
            cwd=Path.cwd(),
        )
        try:
            report = filter_adoption_report(
                report,
                selected_skills,
                strict=True,
            )
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        apply_result = None

    scope = report.scope.capitalize()
    title = "Adopt apply" if apply_mode else "Adopt dry-run"
    click.echo(f"{title} ({scope} scope)")
    click.echo("")
    click.echo(f"Total skills: {report.total_skills}")
    click.echo(f"Needs adoption: {report.needs_adoption}")
    click.echo(f"Duplicate groups: {report.duplicate_groups}")
    click.echo(f"Conflict groups: {report.conflict_groups}")
    if selected_skills:
        click.echo(f"Target filter: {', '.join(selected_skills)}")

    if not report.items:
        click.echo("\nNo skills discovered in known directories.")
        return

    for item in report.items:
        click.echo("")
        click.echo(f"{item.name}")
        click.echo(f"  Ownership: {item.ownership}")
        click.echo(f"  Status: {item.status}")
        click.echo(f"  Action: {item.recommended_action}")
        for location in item.locations:
            tag = "canonical" if location.is_canonical else location.agent
            click.echo(f"  - {tag}: {location.path}")

    click.echo("")
    if not apply_mode:
        click.echo("Dry-run only. No files were modified.")
        return

    if apply_result is None:
        return

    click.echo("Apply complete.")
    click.echo(f"Applied groups: {apply_result.applied_groups}")
    click.echo(f"Linked locations: {apply_result.linked_locations}")
    click.echo(f"Skipped groups: {apply_result.skipped_groups}")
    click.echo(f"Backups created: {len(apply_result.backup_entries)}")
    if apply_result.manifest_path is not None:
        click.echo(f"Manifest: {apply_result.manifest_path}")


def _prompt_apply_skill_selection(
    items: list[AdoptionItem],
) -> list[str] | None:
    """Prompt interactive selection for apply mode.

    Returns ``None`` when user selected all skills.
    """

    if not items:
        return []

    click.echo("")
    click.echo("Select skills to apply:")
    for idx, item in enumerate(items, start=1):
        click.echo(f"  {idx}. {item.name} ({item.status})")
    click.echo("  0. cancel")

    raw = click.prompt(
        "Selection (comma list, 'all', or 0)",
        default="all",
    ).strip()
    lowered = raw.lower()
    if lowered == "all":
        return None
    if lowered in {"0", "none", "cancel"}:
        return []

    names: list[str] = []
    seen: set[str] = set()
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if not token.isdigit():
            raise click.ClickException(
                f"Invalid selection token: {token}"
            )
        number = int(token)
        if number < 1 or number > len(items):
            raise click.ClickException(
                f"Selection out of range: {number}"
            )
        name = items[number - 1].name
        if name in seen:
            continue
        seen.add(name)
        names.append(name)

    return names
