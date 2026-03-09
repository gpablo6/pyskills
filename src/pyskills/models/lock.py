"""Lockfile model definitions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillLockEntry(BaseModel):
    """Global lock entry for a tracked skill installation."""

    source: str
    source_type: str
    source_url: str
    skill_path: str | None = None
    skill_folder_hash: str = ""
    installed_at: str
    updated_at: str
    plugin_name: str | None = None
    source_id: str = ""
    agents: list[str] = Field(default_factory=list)
    install_mode: str = "symlink"


class SkillLockFile(BaseModel):
    """Schema for the global skill lock file."""

    version: int = 1
    skills: dict[str, SkillLockEntry] = Field(default_factory=dict)
    dismissed: dict[str, bool] = Field(default_factory=dict)
    last_selected_agents: list[str] | None = None


class LocalSkillLockEntry(BaseModel):
    """Project lock entry for a tracked skill installation."""

    source: str
    source_type: str
    computed_hash: str


class LocalSkillLockFile(BaseModel):
    """Schema for the project-scoped lock file."""

    version: int = 1
    skills: dict[str, LocalSkillLockEntry] = Field(default_factory=dict)
