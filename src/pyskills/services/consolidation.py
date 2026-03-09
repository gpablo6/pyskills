"""Skill consolidation and adoption diagnostics."""

from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import dataclass, field
from pathlib import Path
import shutil

from pyskills.models import AdoptionBackupEntry, AdoptionManifest
from .agents import AGENTS
from .discovery import parse_skill_md
from .installer import get_agent_base_dir, get_canonical_skills_dir
from .locks import compute_skill_folder_hash, read_global_lock, read_local_lock
from .adoption_manifest import write_adoption_manifest
from pyskills.shared import sanitize_name


@dataclass
class SkillLocation:
    """Represents one discovered skill location."""

    agent: str
    path: Path
    resolved_path: Path
    is_canonical: bool
    content_hash: str | None


@dataclass
class AdoptionItem:
    """Represents one skill analysis entry for consolidation."""

    name: str
    ownership: str
    status: str
    recommended_action: str
    locations: list[SkillLocation] = field(default_factory=list)


@dataclass
class AdoptionReport:
    """Summary report for adopt dry-run."""

    scope: str
    total_skills: int
    needs_adoption: int
    duplicate_groups: int
    conflict_groups: int
    items: list[AdoptionItem]


@dataclass
class ApplyResult:
    """Summary of a consolidation apply execution."""

    applied_groups: int = 0
    linked_locations: int = 0
    skipped_groups: int = 0
    backup_entries: list[AdoptionBackupEntry] = field(default_factory=list)
    created_paths: list[Path] = field(default_factory=list)
    manifest_path: Path | None = None


def filter_adoption_report(
    report: AdoptionReport,
    skill_names: list[str] | None,
    *,
    strict: bool = False,
) -> AdoptionReport:
    """Filter an adoption report by skill names.

    Parameters
    ----------
    report : AdoptionReport
        Source report to filter.
    skill_names : list of str or None
        Optional target skill names.
    strict : bool, optional
        Whether to fail on unknown requested skill names.

    Returns
    -------
    AdoptionReport
        Filtered report with recomputed summary counts.

    Raises
    ------
    ValueError
        Raised when ``strict`` is enabled and names are missing.
    """

    if not skill_names:
        return report

    targets = {name.lower() for name in skill_names}
    items = [
        item for item in report.items if item.name.lower() in targets
    ]

    if strict:
        present = {item.name.lower() for item in report.items}
        missing = sorted(targets - present)
        if missing:
            values = ", ".join(missing)
            raise ValueError(f"Unknown skill target(s): {values}")

    needs_adoption = sum(
        1 for item in items if item.status == "needs-adoption"
    )
    duplicate_groups = sum(1 for item in items if item.status == "duplicate")
    conflict_groups = sum(1 for item in items if item.status == "conflict")

    return AdoptionReport(
        scope=report.scope,
        total_skills=len(items),
        needs_adoption=needs_adoption,
        duplicate_groups=duplicate_groups,
        conflict_groups=conflict_groups,
        items=items,
    )


def build_adoption_report(
    *,
    global_install: bool,
    cwd: Path | None = None,
) -> AdoptionReport:
    """Build a dry-run adoption report.

    Parameters
    ----------
    global_install : bool
        Whether to scan global directories.
    cwd : pathlib.Path or None, optional
        Project root when scanning project scope.

    Returns
    -------
    AdoptionReport
        Consolidation analysis and recommended actions.
    """

    root = cwd or Path.cwd()
    canonical = get_canonical_skills_dir(global_install, cwd=root).resolve()

    ownership_map = _ownership_map(global_install=global_install, cwd=root)
    groups = _scan_skill_groups(
        global_install=global_install,
        root=root,
        canonical=canonical,
    )

    items: list[AdoptionItem] = []
    sorted_groups = sorted(
        groups.items(),
        key=lambda item: item[0].lower(),
    )
    for name, locations in sorted_groups:
        ownership = ownership_map.get(name, "user")
        status, action = _classify_group(locations)
        items.append(
            AdoptionItem(
                name=name,
                ownership=ownership,
                status=status,
                recommended_action=action,
                locations=locations,
            )
        )

    needs_adoption = sum(
        1 for item in items if item.status == "needs-adoption"
    )
    duplicate_groups = sum(1 for item in items if item.status == "duplicate")
    conflict_groups = sum(1 for item in items if item.status == "conflict")

    return AdoptionReport(
        scope="global" if global_install else "project",
        total_skills=len(items),
        needs_adoption=needs_adoption,
        duplicate_groups=duplicate_groups,
        conflict_groups=conflict_groups,
        items=items,
    )


def _ownership_map(
    *,
    global_install: bool,
    cwd: Path,
) -> dict[str, str]:
    """Build skill ownership map from lock files."""

    if global_install:
        lock = read_global_lock()
        return {name: "external" for name in lock.skills.keys()}

    lock = read_local_lock(cwd=cwd)
    return {name: "external" for name in lock.skills.keys()}


def _scan_skill_groups(
    *,
    global_install: bool,
    root: Path,
    canonical: Path,
) -> dict[str, list[SkillLocation]]:
    """Scan known agent directories and group skill locations by name."""

    groups: dict[str, list[SkillLocation]] = {}
    seen_dirs: set[Path] = set()

    scan_dirs: list[tuple[str, Path]] = []
    scan_dirs.append(("canonical", canonical))

    for agent in AGENTS:
        try:
            base = get_agent_base_dir(
                agent,
                global_install,
                cwd=root,
            ).resolve()
        except ValueError:
            continue
        scan_dirs.append((agent, base))

    for agent, base in scan_dirs:
        if base in seen_dirs:
            continue
        seen_dirs.add(base)

        if not base.exists():
            continue

        for child in base.iterdir():
            if not (child.is_dir() or child.is_symlink()):
                continue

            parsed = parse_skill_md(child / "SKILL.md")
            if not parsed:
                continue

            content_hash = _safe_skill_hash(child)
            location = SkillLocation(
                agent=agent,
                path=child,
                resolved_path=child.resolve(),
                is_canonical=_is_under_canonical(child.resolve(), canonical),
                content_hash=content_hash,
            )
            groups.setdefault(parsed.name, []).append(location)

    return groups


def _safe_skill_hash(path: Path) -> str | None:
    """Compute content hash for a skill directory, returning None on errors."""

    try:
        return compute_skill_folder_hash(path)
    except Exception:
        return None


def _is_under_canonical(path: Path, canonical: Path) -> bool:
    """Return whether a path is under canonical skills directory."""

    return path == canonical or canonical in path.parents


def _classify_group(locations: list[SkillLocation]) -> tuple[str, str]:
    """Classify one skill location group and suggest action."""

    has_canonical = any(loc.is_canonical for loc in locations)
    hashes = {loc.content_hash for loc in locations if loc.content_hash}

    if len(locations) == 1:
        if has_canonical:
            return "canonical", "No action needed."
        return (
            "needs-adoption",
            "Adopt into canonical directory and relink agents.",
        )

    if len(hashes) <= 1:
        if has_canonical:
            return (
                "duplicate",
                "Keep canonical copy and replace duplicates with links.",
            )
        return (
            "needs-adoption",
            "Adopt one copy into canonical then relink duplicates.",
        )

    return (
        "conflict",
        "Conflict detected: same skill name has different content."
        " Keep user-authored copy and resolve manually.",
    )


def apply_adoption(
    *,
    global_install: bool,
    cwd: Path | None = None,
    conflict_policy: str = "keep-existing",
    skill_names: list[str] | None = None,
) -> tuple[AdoptionReport, ApplyResult]:
    """Apply consolidation plan to disk.

    Parameters
    ----------
    global_install : bool
        Whether to apply on global directories.
    cwd : pathlib.Path or None, optional
        Project root when applying in project scope.
    conflict_policy : {"keep-existing", "use-canonical"}, optional
        Conflict behavior for groups with differing content.
    skill_names : list of str or None, optional
        Optional subset of skills to apply.

    Returns
    -------
    tuple of AdoptionReport and ApplyResult
        The discovery report and execution summary.
    """

    if conflict_policy not in {"keep-existing", "use-canonical"}:
        raise ValueError("Unsupported conflict policy")

    root = cwd or Path.cwd()
    canonical_base = get_canonical_skills_dir(
        global_install=global_install,
        cwd=root,
    )
    canonical_base.mkdir(parents=True, exist_ok=True)

    report = build_adoption_report(global_install=global_install, cwd=root)
    report = filter_adoption_report(
        report,
        skill_names,
        strict=True,
    )
    result = ApplyResult()

    if not report.items:
        return report, result

    for item in report.items:
        canonical_path = canonical_base / sanitize_name(item.name)
        canonical_loc = _find_canonical_location(
            item.locations,
            canonical_path,
        )

        if item.status == "conflict" and conflict_policy == "keep-existing":
            result.skipped_groups += 1
            continue

        chosen = canonical_loc or _pick_primary_location(item.locations)
        if chosen is None:
            result.skipped_groups += 1
            continue

        if not canonical_path.exists() and not canonical_path.is_symlink():
            _copy_skill_directory(chosen.path, canonical_path)
            result.applied_groups += 1
            result.created_paths.append(canonical_path)

        if item.status in {"needs-adoption", "duplicate"}:
            linked = _link_non_canonical(
                locations=item.locations,
                canonical_path=canonical_path,
                backup_entries=result.backup_entries,
            )
            result.linked_locations += linked
            if item.status == "duplicate":
                result.applied_groups += 1
            continue

        if item.status == "conflict":
            linked = _link_non_canonical(
                locations=item.locations,
                canonical_path=canonical_path,
                backup_entries=result.backup_entries,
            )
            result.linked_locations += linked
            result.applied_groups += 1
            continue

    changed = bool(result.backup_entries or result.created_paths)
    if not changed:
        return report, result

    manifest = AdoptionManifest(
        created_at=datetime.now(UTC).isoformat(),
        scope="global" if global_install else "project",
        conflict_policy=conflict_policy,
        backup_entries=result.backup_entries,
        created_paths=[str(path.resolve()) for path in result.created_paths],
    )
    manifest_dir = canonical_base.parent / ".adopt-manifests"
    result.manifest_path = write_adoption_manifest(
        manifest=manifest,
        base_dir=manifest_dir,
    )

    return report, result


def _find_canonical_location(
    locations: list[SkillLocation],
    canonical_path: Path,
) -> SkillLocation | None:
    """Find the canonical location for a skill when available."""

    for location in locations:
        if location.path.resolve() == canonical_path.resolve():
            return location
        if location.is_canonical:
            return location
    return None


def _pick_primary_location(
    locations: list[SkillLocation],
) -> SkillLocation | None:
    """Choose a stable source location for adoption."""

    if not locations:
        return None
    return sorted(locations, key=lambda loc: str(loc.path))[0]


def _copy_skill_directory(src: Path, dst: Path) -> None:
    """Copy one skill directory to destination path."""

    if dst.exists() or dst.is_symlink():
        shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        if entry.name in {"metadata.json", ".git"}:
            continue
        if entry.name.startswith("_"):
            continue
        target = dst / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target)
        else:
            shutil.copy2(entry, target)


def _link_non_canonical(
    *,
    locations: list[SkillLocation],
    canonical_path: Path,
    backup_entries: list[AdoptionBackupEntry],
) -> int:
    """Replace non-canonical locations with links to canonical path."""

    linked = 0
    for location in locations:
        src = location.path
        if src.resolve() == canonical_path.resolve():
            continue
        _replace_with_symlink(
            source_path=src,
            target_path=canonical_path,
            backup_entries=backup_entries,
        )
        linked += 1
    return linked


def _replace_with_symlink(
    *,
    source_path: Path,
    target_path: Path,
    backup_entries: list[AdoptionBackupEntry],
) -> None:
    """Replace one path with a symlink to the canonical directory."""

    source_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.exists() or source_path.is_symlink():
        backup = _backup_path(source_path)
        shutil.move(str(source_path), str(backup))
        backup_entries.append(
            AdoptionBackupEntry(
                original_path=str(source_path.resolve()),
                backup_path=str(backup.resolve()),
            )
        )

    try:
        source_path.symlink_to(target_path, target_is_directory=True)
    except OSError:
        _copy_skill_directory(target_path, source_path)


def _backup_path(path: Path) -> Path:
    """Generate a unique backup path for an existing skill path."""

    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    candidate = path.with_name(f"{path.name}.bak-{stamp}")
    suffix = 1
    while candidate.exists() or candidate.is_symlink():
        candidate = path.with_name(
            f"{path.name}.bak-{stamp}-{suffix}"
        )
        suffix += 1
    return candidate
