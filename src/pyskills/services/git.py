"""Git clone and temporary workspace services."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


class GitCloneError(RuntimeError):
    """Raised when cloning a repository fails."""


def clone_repo(url: str, ref: str | None = None) -> Path:
    """Clone a repository into a temporary directory.

    Parameters
    ----------
    url : str
        Repository URL or git-compatible source.
    ref : str or None, optional
        Optional branch or tag to checkout during shallow clone.

    Returns
    -------
    pathlib.Path
        Temporary directory containing the cloned repository.

    Raises
    ------
    GitCloneError
        Raised when ``git clone`` fails.
    """

    from git import GitCommandError, Repo

    temp_dir = Path(tempfile.mkdtemp(prefix="pyskills-"))

    try:
        if ref:
            Repo.clone_from(
                url,
                temp_dir,
                branch=ref,
                multi_options=["--depth=1"],
            )
        else:
            Repo.clone_from(
                url,
                temp_dir,
                multi_options=["--depth=1"],
            )
    except GitCommandError as exc:
        cleanup_temp_dir(temp_dir)
        stderr = str(exc).strip() or "unknown error"
        raise GitCloneError(f"failed to clone {url}: {stderr}") from exc

    return temp_dir


def cleanup_temp_dir(path: Path) -> None:
    """Remove a temporary clone directory.

    Parameters
    ----------
    path : pathlib.Path
        Temporary directory path created by ``clone_repo``.

    Returns
    -------
    None
    """

    shutil.rmtree(path, ignore_errors=True)
