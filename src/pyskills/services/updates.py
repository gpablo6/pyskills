"""Update detection services for globally tracked skills."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

from pyskills.models import SkillLockEntry

from .git import cleanup_temp_dir
from .locks import compute_skill_folder_hash, read_global_lock
from .well_known import WellKnownError, materialize_well_known_source


@dataclass
class OutdatedSkill:
    """Represents one lock-tracked skill that has an available update."""

    name: str
    entry: SkillLockEntry
    latest_hash: str


@dataclass
class SkippedSkill:
    """Represents one skill skipped during update checks."""

    name: str
    reason: str


def check_global_updates(
    *,
    verbose: bool = False,
) -> tuple[list[OutdatedSkill], list[SkippedSkill]]:
    """Check global lock entries and return outdated and skipped skills.

    Parameters
    ----------
    verbose : bool, optional
        Whether to include verbose skip reasons for unsupported sources.

    Returns
    -------
    tuple of list
        Outdated skills and skipped entries.
    """

    lock = read_global_lock()
    outdated: list[OutdatedSkill] = []
    skipped: list[SkippedSkill] = []

    for name, entry in lock.skills.items():
        source_type = entry.source_type
        if source_type == "github":
            _check_github_entry(name, entry, outdated, skipped)
            continue
        if source_type == "well-known":
            _check_well_known_entry(name, entry, outdated, skipped)
            continue
        if source_type == "local":
            _check_local_entry(name, entry, outdated, skipped)
            continue

        if verbose:
            skipped.append(
                SkippedSkill(
                    name=name,
                    reason=f"Unsupported source type: {source_type}",
                )
            )

    return outdated, skipped


def parse_github_owner_repo(value: str) -> str | None:
    """Parse ``owner/repo`` from common GitHub source formats."""

    if value.startswith("https://github.com/"):
        tail = value.removeprefix("https://github.com/")
        tail = tail.removesuffix(".git").strip("/")
        parts = tail.split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"

    if value.startswith("git@github.com:"):
        tail = value.removeprefix("git@github.com:")
        tail = tail.removesuffix(".git").strip("/")
        parts = tail.split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"

    parts = value.strip().split("/")
    if len(parts) == 2 and all(parts):
        return f"{parts[0]}/{parts[1]}"

    return None


def fetch_github_skill_folder_hash(
    owner_repo: str,
    skill_path: str,
    token: str | None = None,
) -> str | None:
    """Fetch folder tree hash for a skill path from GitHub trees API."""

    folder = _skill_folder_path(skill_path)
    branches = ["main", "master"]

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for branch in branches:
        url = (
            f"https://api.github.com/repos/{owner_repo}"
            f"/git/trees/{branch}?recursive=1"
        )

        try:
            response = httpx.get(url, headers=headers, timeout=10.0)
        except httpx.HTTPError:
            continue

        if response.status_code >= 400:
            continue

        try:
            payload = response.json()
        except ValueError:
            continue

        root_sha = payload.get("sha") if isinstance(payload, dict) else None
        tree = payload.get("tree") if isinstance(payload, dict) else None

        if folder == "":
            return root_sha if isinstance(root_sha, str) else None

        if not isinstance(tree, list):
            continue

        for entry in tree:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path")
            item_type = entry.get("type")
            sha = entry.get("sha")
            if path == folder and item_type == "tree" and isinstance(sha, str):
                return sha

    return None


def build_update_install_url(entry: SkillLockEntry) -> str:
    """Build install URL targeting the tracked skill folder when possible."""

    if entry.source_type == "well-known":
        source = entry.source_url.rstrip("/")
        if not entry.skill_path:
            return source
        skill_name = _skill_name_from_path(entry.skill_path)
        if not skill_name:
            return source
        return f"{source}/.well-known/skills/{skill_name}"

    if entry.source_type == "local":
        return entry.source_url

    source = entry.source_url.removesuffix(".git").rstrip("/")
    if not entry.skill_path:
        return source

    folder = _skill_folder_path(entry.skill_path)
    if not folder:
        return source

    return f"{source}/tree/main/{folder}"


def _skill_folder_path(skill_path: str) -> str:
    """Normalize lock skill path to folder path."""

    path = skill_path.replace("\\", "/")
    if path.endswith("/SKILL.md"):
        path = path[: -len("/SKILL.md")]
    elif path.endswith("SKILL.md"):
        path = path[: -len("SKILL.md")]

    return path.rstrip("/")


def _skill_name_from_path(skill_path: str) -> str | None:
    """Extract top-level skill directory name from lock skill path."""

    normalized = skill_path.replace("\\", "/").strip("/")
    if not normalized:
        return None
    parts = normalized.split("/")
    if not parts:
        return None
    return parts[0] or None


def _check_github_entry(
    name: str,
    entry: SkillLockEntry,
    outdated: list[OutdatedSkill],
    skipped: list[SkippedSkill],
) -> None:
    """Check whether one GitHub lock entry is outdated."""

    if not entry.skill_path:
        skipped.append(SkippedSkill(name=name, reason="Missing skill path"))
        return
    if not entry.skill_folder_hash:
        skipped.append(SkippedSkill(name=name, reason="Missing folder hash"))
        return

    owner_repo = parse_github_owner_repo(entry.source_url)
    if not owner_repo:
        skipped.append(
            SkippedSkill(name=name, reason="Unparseable GitHub source")
        )
        return

    latest = fetch_github_skill_folder_hash(owner_repo, entry.skill_path)
    if not latest:
        skipped.append(SkippedSkill(name=name, reason="Hash lookup failed"))
        return

    if latest != entry.skill_folder_hash:
        outdated.append(
            OutdatedSkill(name=name, entry=entry, latest_hash=latest)
        )


def _check_well_known_entry(
    name: str,
    entry: SkillLockEntry,
    outdated: list[OutdatedSkill],
    skipped: list[SkippedSkill],
) -> None:
    """Check whether one well-known lock entry is outdated."""

    if not entry.skill_path:
        skipped.append(SkippedSkill(name=name, reason="Missing skill path"))
        return
    if not entry.skill_folder_hash:
        skipped.append(SkippedSkill(name=name, reason="Missing folder hash"))
        return

    skill_name = _skill_name_from_path(entry.skill_path)
    if not skill_name:
        skipped.append(
            SkippedSkill(name=name, reason="Unparseable well-known skill path")
        )
        return

    temp_dir: Path | None = None
    try:
        temp_dir = materialize_well_known_source(
            entry.source_url,
            skill_filter=skill_name,
        )
        latest_hash = compute_skill_folder_hash(temp_dir / skill_name)
    except (WellKnownError, OSError):
        skipped.append(
            SkippedSkill(name=name, reason="Well-known fetch failed")
        )
        return
    finally:
        if temp_dir is not None:
            cleanup_temp_dir(temp_dir)

    if latest_hash != entry.skill_folder_hash:
        outdated.append(
            OutdatedSkill(name=name, entry=entry, latest_hash=latest_hash)
        )


def _check_local_entry(
    name: str,
    entry: SkillLockEntry,
    outdated: list[OutdatedSkill],
    skipped: list[SkippedSkill],
) -> None:
    """Check whether one local-source lock entry is outdated."""

    if not entry.skill_path:
        skipped.append(SkippedSkill(name=name, reason="Missing skill path"))
        return
    if not entry.skill_folder_hash:
        skipped.append(SkippedSkill(name=name, reason="Missing folder hash"))
        return

    source_root = Path(entry.source_url)
    if not source_root.exists():
        skipped.append(SkippedSkill(name=name, reason="Local source missing"))
        return

    folder = _skill_folder_path(entry.skill_path)
    target = source_root / folder if folder else source_root
    if not target.exists():
        skipped.append(
            SkippedSkill(name=name, reason="Local skill path missing")
        )
        return

    latest_hash = compute_skill_folder_hash(target)
    if latest_hash != entry.skill_folder_hash:
        outdated.append(
            OutdatedSkill(name=name, entry=entry, latest_hash=latest_hash)
        )
