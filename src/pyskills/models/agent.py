"""Agent model definitions."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Configuration describing an agent's skill directories.

    Attributes
    ----------
    name : str
        Internal agent identifier.
    display_name : str
        Human-readable agent name.
    skills_dir : pathlib.Path
        Project-scoped skills directory relative path.
    global_skills_dir : pathlib.Path or None
        Global skills directory. ``None`` means global installs are
        unsupported.
    show_in_universal_list : bool
        Whether the agent appears in universal selection views.
    """

    name: str
    display_name: str
    skills_dir: Path
    global_skills_dir: Path | None = None
    show_in_universal_list: bool = True
