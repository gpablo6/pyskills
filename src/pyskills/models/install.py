"""Installation-related models."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

InstallMode = Literal["symlink", "copy"]


class InstallResult(BaseModel):
    """Result payload for skill installation actions.

    Attributes
    ----------
    success : bool
        Whether installation completed successfully.
    path : pathlib.Path
        Final install path for the target agent.
    mode : {"symlink", "copy"}
        Installation strategy used.
    canonical_path : pathlib.Path or None
        Canonical skill path when symlink mode is used.
    symlink_failed : bool
        Whether symlink creation failed and fallback copy was used.
    error : str or None
        Error message for unsuccessful operations.
    """

    success: bool
    path: Path
    mode: InstallMode
    canonical_path: Path | None = None
    symlink_failed: bool = False
    error: str | None = None
