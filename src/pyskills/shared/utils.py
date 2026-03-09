"""Shared utility helpers."""

from __future__ import annotations

from pathlib import Path


def is_subpath_safe(base_path: Path, target_path: Path) -> bool:
    """Check whether ``target_path`` remains inside ``base_path``.

    Parameters
    ----------
    base_path : pathlib.Path
        Trusted base directory.
    target_path : pathlib.Path
        Candidate path to validate.

    Returns
    -------
    bool
        ``True`` when target resolves within base.
    """

    base = base_path.resolve()
    target = target_path.resolve()
    return target == base or base in target.parents


def sanitize_name(name: str) -> str:
    """Sanitize a filesystem skill name.

    Parameters
    ----------
    name : str
        Raw skill name.

    Returns
    -------
    str
        Safe normalized name suitable for directory creation.
    """

    lowered = name.lower()
    out: list[str] = []
    last_hyphen = False

    for ch in lowered:
        allowed = ch.isalnum() or ch in "._"
        if allowed:
            out.append(ch)
            last_hyphen = False
            continue
        if not last_hyphen:
            out.append("-")
            last_hyphen = True

    cleaned = "".join(out).strip(".-")
    return cleaned[:255] or "unnamed-skill"
