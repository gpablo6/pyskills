import httpx
from pathlib import Path

from pyskills.models import SkillLockEntry, SkillLockFile
from pyskills.services.updates import (
    build_update_install_url,
    check_global_updates,
    fetch_github_skill_folder_hash,
    parse_github_owner_repo,
)


def _entry(**kwargs):  # noqa: ANN003, ANN201
    defaults = {
        "source": "https://github.com/acme/repo.git",
        "source_type": "github",
        "source_url": "https://github.com/acme/repo.git",
        "skill_path": "skills/demo/SKILL.md",
        "skill_folder_hash": "old",
        "installed_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    defaults.update(kwargs)
    return SkillLockEntry(**defaults)


def test_parse_github_owner_repo_variants() -> None:
    assert parse_github_owner_repo("https://github.com/a/b.git") == "a/b"
    assert parse_github_owner_repo("git@github.com:a/b.git") == "a/b"
    assert parse_github_owner_repo("a/b") == "a/b"
    assert parse_github_owner_repo("https://gitlab.com/a/b") is None


def test_build_update_install_url_uses_skill_folder() -> None:
    entry = _entry(skill_path="skills/demo/SKILL.md")
    url = build_update_install_url(entry)
    assert url == "https://github.com/acme/repo/tree/main/skills/demo"


def test_fetch_github_skill_folder_hash(monkeypatch) -> None:
    class MockResponse:
        status_code = 200

        def json(self):  # noqa: ANN201
            return {
                "sha": "root",
                "tree": [
                    {
                        "path": "skills/demo",
                        "type": "tree",
                        "sha": "hash123",
                    }
                ],
            }

    def fake_get(url: str, headers: dict, timeout: float):  # noqa: ANN001, ANN201, ARG001
        return MockResponse()

    monkeypatch.setattr(httpx, "get", fake_get)
    value = fetch_github_skill_folder_hash("acme/repo", "skills/demo/SKILL.md")
    assert value == "hash123"


def test_check_global_updates_marks_outdated(monkeypatch) -> None:
    lock = SkillLockFile(version=1, skills={"demo": _entry()})

    monkeypatch.setattr(
        "pyskills.services.updates.read_global_lock",
        lambda: lock,
    )
    monkeypatch.setattr(
        "pyskills.services.updates.fetch_github_skill_folder_hash",
        lambda owner_repo, skill_path: "newhash",  # noqa: ARG005
    )

    outdated, skipped = check_global_updates()
    assert len(outdated) == 1
    assert outdated[0].name == "demo"
    assert skipped == []


def test_check_global_updates_verbose_skips_unsupported(monkeypatch) -> None:
    lock = SkillLockFile(
        version=1,
        skills={
            "demo": _entry(source_type="zip", source_url="https://x"),
        },
    )

    monkeypatch.setattr(
        "pyskills.services.updates.read_global_lock",
        lambda: lock,
    )

    outdated, skipped = check_global_updates(verbose=True)
    assert outdated == []
    assert skipped
    assert skipped[0].reason.startswith("Unsupported source type")


def test_check_global_updates_well_known_outdated(
    monkeypatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "remote"
    skill_dir = root / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: demo\n---\n",
        encoding="utf-8",
    )
    entry = _entry(
        source_type="well-known",
        source_url="https://example.com",
        skill_path="demo/SKILL.md",
        skill_folder_hash="old",
    )
    lock = SkillLockFile(version=1, skills={"demo": entry})

    monkeypatch.setattr(
        "pyskills.services.updates.read_global_lock",
        lambda: lock,
    )
    monkeypatch.setattr(
        "pyskills.services.updates.materialize_well_known_source",
        lambda source_url, skill_filter: root,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "pyskills.services.updates.compute_skill_folder_hash",
        lambda path: "newhash",  # noqa: ARG005
    )
    monkeypatch.setattr(
        "pyskills.services.updates.cleanup_temp_dir",
        lambda path: None,  # noqa: ARG005
    )

    outdated, skipped = check_global_updates()
    assert len(outdated) == 1
    assert skipped == []


def test_check_global_updates_local_source_missing(monkeypatch) -> None:
    entry = _entry(
        source_type="local",
        source_url="/tmp/missing-root",
        skill_path="demo/SKILL.md",
    )
    lock = SkillLockFile(version=1, skills={"demo": entry})

    monkeypatch.setattr(
        "pyskills.services.updates.read_global_lock",
        lambda: lock,
    )

    outdated, skipped = check_global_updates()
    assert outdated == []
    assert skipped
    assert skipped[0].reason == "Local source missing"


def test_fetch_github_skill_folder_hash_root_sha(monkeypatch) -> None:
    class MockResponse:
        status_code = 200

        def json(self):  # noqa: ANN201
            return {"sha": "root-sha", "tree": []}

    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, headers, timeout: MockResponse(),  # noqa: ARG005
    )
    value = fetch_github_skill_folder_hash("acme/repo", "SKILL.md")
    assert value == "root-sha"


def test_build_update_install_url_well_known_without_skill_path() -> None:
    entry = _entry(
        source_type="well-known",
        source_url="https://example.com/",
        skill_path=None,
    )
    assert build_update_install_url(entry) == "https://example.com"
