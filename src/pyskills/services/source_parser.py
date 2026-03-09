"""Input source parsing services."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from pyskills.models import ParsedSource, SourceType


SOURCE_ALIASES: dict[str, str] = {
    "coinbase/agentWallet": "coinbase/agentic-wallet-skills",
}


def sanitize_subpath(subpath: str) -> str:
    """Validate and return a safe repository subpath.

    Parameters
    ----------
    subpath : str
        User-provided subpath.

    Returns
    -------
    str
        Original subpath if valid.

    Raises
    ------
    ValueError
        Raised when traversal components such as ``..`` are present.
    """

    normalized = subpath.replace("\\", "/")
    for segment in normalized.split("/"):
        if segment == "..":
            raise ValueError(
                f'Unsafe subpath: "{subpath}" contains path traversal segments'
            )
    return subpath


def _is_local_path(value: str) -> bool:
    """Check whether a source string should be treated as local path.

    Parameters
    ----------
    value : str
        Raw source input.

    Returns
    -------
    bool
        ``True`` when local path heuristics match.
    """

    if value in {".", ".."}:
        return True
    if value.startswith("./") or value.startswith("../"):
        return True
    if re.match(r"^[A-Za-z]:[/\\]", value):
        return True
    return Path(value).is_absolute()


def _is_well_known_url(value: str) -> bool:
    """Check whether a URL should use well-known source handling.

    Parameters
    ----------
    value : str
        Raw source input.

    Returns
    -------
    bool
        ``True`` when the input is HTTP(S), non-git-host, and not a
        ``.git`` URL.
    """

    if not (value.startswith("http://") or value.startswith("https://")):
        return False
    parsed = urlparse(value)
    if parsed.hostname in {
        "github.com",
        "gitlab.com",
        "raw.githubusercontent.com",
    }:
        return False
    if value.endswith(".git"):
        return False
    return True


def _well_known_skill_filter(value: str) -> str | None:
    """Extract skill filter from a direct well-known skill URL.

    Parameters
    ----------
    value : str
        Raw source URL.

    Returns
    -------
    str or None
        Skill name when URL matches ``/.well-known/skills/<name>``.
    """

    parsed = urlparse(value)
    path = parsed.path.rstrip("/")
    match = re.search(r"/\.well-known/skills/([^/]+)$", path)
    if not match:
        return None
    return match.group(1)


def parse_source(source: str) -> ParsedSource:
    """Parse a source string into a structured source model.

    Parameters
    ----------
    source : str
        User-provided source value.

    Returns
    -------
    ParsedSource
        Parsed and normalized source representation.
    """

    source = SOURCE_ALIASES.get(source, source)

    github_pref = re.match(r"^github:(.+)$", source)
    if github_pref:
        return parse_source(github_pref.group(1))

    gitlab_pref = re.match(r"^gitlab:(.+)$", source)
    if gitlab_pref:
        return parse_source(f"https://gitlab.com/{gitlab_pref.group(1)}")

    if _is_local_path(source):
        resolved = Path(source).resolve()
        return ParsedSource(
            type=SourceType.LOCAL, url=str(resolved), local_path=resolved
        )

    m = re.match(r".*github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)", source)
    if m:
        owner, repo, ref, subpath = m.groups()
        return ParsedSource(
            type=SourceType.GITHUB,
            url=f"https://github.com/{owner}/{repo}.git",
            ref=ref,
            subpath=sanitize_subpath(subpath),
        )

    m = re.match(r".*github\.com/([^/]+)/([^/]+)/tree/([^/]+)$", source)
    if m:
        owner, repo, ref = m.groups()
        return ParsedSource(
            type=SourceType.GITHUB,
            url=f"https://github.com/{owner}/{repo}.git",
            ref=ref,
        )

    m = re.match(r".*github\.com/([^/]+)/([^/]+)", source)
    if m:
        owner, repo = m.groups()
        repo = repo.removesuffix(".git")
        return ParsedSource(
            type=SourceType.GITHUB,
            url=f"https://github.com/{owner}/{repo}.git",
        )

    m = re.match(r"^([^/]+)/([^/@]+)@(.+)$", source)
    if m and ":" not in source and not source.startswith((".", "/")):
        owner, repo, skill_filter = m.groups()
        return ParsedSource(
            type=SourceType.GITHUB,
            url=f"https://github.com/{owner}/{repo}.git",
            skill_filter=skill_filter,
        )

    m = re.match(r"^([^/]+)/([^/]+)(?:/(.+))?$", source)
    if m and ":" not in source and not source.startswith((".", "/")):
        owner, repo, subpath = m.groups()
        return ParsedSource(
            type=SourceType.GITHUB,
            url=f"https://github.com/{owner}/{repo}.git",
            subpath=sanitize_subpath(subpath) if subpath else None,
        )

    if _is_well_known_url(source):
        return ParsedSource(
            type=SourceType.WELL_KNOWN,
            url=source,
            skill_filter=_well_known_skill_filter(source),
        )

    return ParsedSource(type=SourceType.GIT, url=source)
