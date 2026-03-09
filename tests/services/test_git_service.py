from pathlib import Path

import pytest
from git import GitCommandError, Repo

from pyskills.services.git import GitCloneError, cleanup_temp_dir, clone_repo


def test_clone_repo_success(monkeypatch) -> None:
    called = {"value": False}

    def fake_clone_from(  # noqa: ANN001, ANN201
        url,
        to_path,
        branch=None,
        multi_options=None,
    ):
        called["value"] = True
        Path(to_path).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(Repo, "clone_from", fake_clone_from)

    path = clone_repo("https://example.com/repo.git")
    assert path.exists()
    assert called["value"]
    cleanup_temp_dir(path)


def test_clone_repo_wraps_git_errors(monkeypatch) -> None:
    def fail_clone(  # noqa: ANN001, ANN201, ARG001
        url,
        to_path,
        branch=None,
        multi_options=None,
    ):
        raise GitCommandError("clone", 1, stderr="bad auth")

    monkeypatch.setattr(Repo, "clone_from", fail_clone)

    with pytest.raises(GitCloneError):
        clone_repo("https://example.com/private.git")


def test_cleanup_temp_dir_removes_directory(tmp_path: Path) -> None:
    target = tmp_path / "tmp"
    target.mkdir(parents=True)
    (target / "x.txt").write_text("x", encoding="utf-8")

    cleanup_temp_dir(target)
    assert not target.exists()
