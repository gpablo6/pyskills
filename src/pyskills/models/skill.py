"""Skill model definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel


class Skill(BaseModel):
    """Represents a discovered skill directory.

    Attributes
    ----------
    name : str
        Skill name from frontmatter.
    description : str
        Skill description from frontmatter.
    path : pathlib.Path
        Filesystem path of the skill directory.
    raw_content : str or None
        Raw ``SKILL.md`` content if captured during parse.
    plugin_name : str or None
        Optional plugin/group name.
    metadata : dict or None
        Arbitrary metadata from frontmatter.
    """

    name: str
    description: str
    path: Path
    raw_content: str | None = None
    plugin_name: str | None = None
    metadata: dict[str, Any] | None = None
