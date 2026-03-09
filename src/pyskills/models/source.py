"""Source model definitions."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel


class SourceType(str, Enum):
    """Enumerates supported source identifiers."""

    GITHUB = "github"
    GITLAB = "gitlab"
    GIT = "git"
    LOCAL = "local"
    WELL_KNOWN = "well-known"


class ParsedSource(BaseModel):
    """Structured source result returned by parsing input strings.

    Attributes
    ----------
    type : SourceType
        Classified source type.
    url : str
        Canonical URL or resolved local path string.
    subpath : str or None
        Optional subpath within a repository or base directory.
    local_path : pathlib.Path or None
        Resolved local path for local sources.
    ref : str or None
        Optional git reference (branch or tag).
    skill_filter : str or None
        Optional explicit skill name filter from ``owner/repo@skill`` syntax.
    """

    type: SourceType
    url: str
    subpath: str | None = None
    local_path: Path | None = None
    ref: str | None = None
    skill_filter: str | None = None
