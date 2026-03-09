"""Shared filesystem constants used across services."""

from pathlib import Path

AGENTS_DIR = Path(".agents")
SKILLS_SUBDIR = Path("skills")
UNIVERSAL_SKILLS_DIR = AGENTS_DIR / SKILLS_SUBDIR
LOCAL_LOCK_FILE = Path("skills-lock.json")
GLOBAL_LOCK_FILE = Path(".skill-lock.json")
