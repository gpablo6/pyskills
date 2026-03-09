"""Well-known skills source services.

This module supports fetching skills from RFC-style well-known endpoints,
materializing files locally, and returning a discovery-ready directory.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlparse

import httpx

from pyskills.shared import is_subpath_safe


class WellKnownError(RuntimeError):
    """Raised when well-known source fetch or validation fails."""


class WellKnownEntry(TypedDict):
    """Typed representation of a skill entry from index.json."""

    name: str
    description: str
    files: list[str]


def materialize_well_known_source(
    url: str,
    skill_filter: str | None = None,
) -> Path:
    """Fetch and materialize skills from a well-known endpoint.

    Parameters
    ----------
    url : str
        Base URL or well-known URL pointing to skills endpoint.
    skill_filter : str or None, optional
        Optional skill name to limit downloaded entries.

    Returns
    -------
    pathlib.Path
        Temporary directory containing one subdirectory per skill.

    Raises
    ------
    WellKnownError
        Raised when index fetch, validation, filtering, or file download fails.
    """

    index_data, base_url, path_skill = _fetch_index(url)
    entries = _validate_entries(index_data)

    requested = skill_filter or path_skill
    if requested:
        entries = [entry for entry in entries if entry["name"] == requested]
        if not entries:
            raise WellKnownError(
                f"Skill '{requested}' not found in well-known index"
            )

    temp_dir = Path(tempfile.mkdtemp(prefix="pyskills-wellknown-"))

    for entry in entries:
        skill_name = entry["name"]
        files = entry["files"]

        skill_dir = temp_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        for rel_path in files:
            dest = skill_dir / rel_path
            if not is_subpath_safe(skill_dir, dest):
                raise WellKnownError(
                    f"Unsafe file path '{rel_path}' in skill '{skill_name}'"
                )

            file_url = f"{base_url}/.well-known/skills/{skill_name}/{rel_path}"
            content = _fetch_text(file_url)

            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")

    return temp_dir


def _fetch_index(url: str) -> tuple[dict[str, object], str, str | None]:
    """Fetch well-known index and infer requested skill path.

    Parameters
    ----------
    url : str
        User-provided URL.

    Returns
    -------
    tuple
        ``(index_data, resolved_base_url, requested_skill_name)``.

    Raises
    ------
    WellKnownError
        Raised when no valid index endpoint can be retrieved.
    """

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise WellKnownError("Well-known source must be a valid HTTP(S) URL")

    base_path = parsed.path.rstrip("/")
    path_skill = _skill_from_path(base_path)

    candidates: list[tuple[str, str]] = []
    candidates.append(
        (
            f"{parsed.scheme}://{parsed.netloc}{base_path}",
            (
                f"{parsed.scheme}://{parsed.netloc}{base_path}"
                "/.well-known/skills/index.json"
            ),
        )
    )

    if base_path and base_path not in {"/.well-known", "/.well-known/skills"}:
        candidates.append(
            (
                f"{parsed.scheme}://{parsed.netloc}",
                (
                    f"{parsed.scheme}://{parsed.netloc}"
                    "/.well-known/skills/index.json"
                ),
            )
        )

    for base_url, index_url in candidates:
        try:
            response = httpx.get(index_url, timeout=10.0)
            if response.status_code >= 400:
                continue
            data = response.json()
            if isinstance(data, dict):
                return data, base_url, path_skill
        except (httpx.HTTPError, ValueError):
            continue

    raise WellKnownError(
        "Could not fetch a valid /.well-known/skills/index.json"
    )


def _skill_from_path(path: str) -> str | None:
    """Extract skill name from explicit well-known URL path.

    Parameters
    ----------
    path : str
        URL path component.

    Returns
    -------
    str or None
        Skill name when URL targets ``/.well-known/skills/<name>``.
    """

    match = re.search(r"/\.well-known/skills/([^/]+)$", path)
    if not match:
        return None
    return match.group(1)


def _validate_entries(index_data: dict[str, object]) -> list[WellKnownEntry]:
    """Validate and return skill entries from index payload.

    Parameters
    ----------
    index_data : dict
        Parsed index JSON payload.

    Returns
    -------
    list of dict
        Validated list of skill entries.

    Raises
    ------
    WellKnownError
        Raised when index shape or entry data is invalid.
    """

    skills = index_data.get("skills")
    if not isinstance(skills, list) or not skills:
        raise WellKnownError(
            "well-known index must include a non-empty 'skills' list"
        )

    entries: list[WellKnownEntry] = []
    for item in skills:
        if not isinstance(item, dict):
            raise WellKnownError("skill entry must be an object")

        name = item.get("name")
        desc = item.get("description")
        files = item.get("files")

        if not isinstance(name, str) or not name:
            raise WellKnownError("skill entry missing valid 'name'")
        if not isinstance(desc, str) or not desc:
            raise WellKnownError(f"skill '{name}' missing valid 'description'")
        if not isinstance(files, list) or not files:
            raise WellKnownError(f"skill '{name}' missing valid 'files'")

        validated_files: list[str] = []
        for file_name in files:
            if not isinstance(file_name, str) or not file_name:
                raise WellKnownError(f"skill '{name}' has invalid file path")
            starts_absolute = file_name.startswith(("/", "\\"))
            has_traversal = ".." in file_name.split("/")
            if starts_absolute or has_traversal:
                raise WellKnownError(
                    f"skill '{name}' has unsafe file path '{file_name}'"
                )
            validated_files.append(file_name)

        has_skill_md = any(f.lower() == "skill.md" for f in validated_files)
        if not has_skill_md:
            raise WellKnownError(
                f"skill '{name}' is missing required SKILL.md file"
            )

        entries.append(
            {
                "name": name,
                "description": desc,
                "files": validated_files,
            }
        )

    return entries


def _fetch_text(url: str) -> str:
    """Fetch UTF-8 text content from a URL.

    Parameters
    ----------
    url : str
        HTTP(S) URL.

    Returns
    -------
    str
        Response body text.

    Raises
    ------
    WellKnownError
        Raised when request fails or response status is unsuccessful.
    """

    try:
        response = httpx.get(url, timeout=10.0)
    except httpx.HTTPError as exc:
        raise WellKnownError(f"Failed to fetch {url}: {exc}") from exc

    if response.status_code >= 400:
        raise WellKnownError(
            f"Failed to fetch {url}: HTTP {response.status_code}"
        )

    return response.text
