"""Adoption manifest model definitions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AdoptionBackupEntry(BaseModel):
    """Backup operation entry recorded during adoption apply."""

    original_path: str
    backup_path: str


class AdoptionManifest(BaseModel):
    """Schema for an adoption apply manifest."""

    version: int = 1
    created_at: str
    scope: str
    conflict_policy: str
    backup_entries: list[AdoptionBackupEntry] = Field(default_factory=list)
    created_paths: list[str] = Field(default_factory=list)
