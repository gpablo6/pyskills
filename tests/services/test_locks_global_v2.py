import json
from pathlib import Path

from pyskills.services.locks import (
    add_skill_to_global_lock,
    read_global_lock,
    remove_skill_agents_from_global_lock,
)


def test_read_global_lock_migrates_v1(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    lock_dir = tmp_path / ".agents"
    lock_dir.mkdir(parents=True)
    lock_file = lock_dir / ".skill-lock.json"
    lock_file.write_text(
        json.dumps(
            {
                "version": 1,
                "skills": {
                    "demo": {
                        "source": "https://github.com/acme/repo.git",
                        "source_type": "github",
                        "source_url": "https://github.com/acme/repo.git",
                        "skill_path": "skills/demo/SKILL.md",
                        "skill_folder_hash": "abc",
                        "installed_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-01T00:00:00Z",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    lock = read_global_lock()
    assert lock.version == 2
    assert "demo" in lock.skills
    assert lock.skills["demo"].source_id == "acme/repo"
    assert lock.skills["demo"].install_mode == "symlink"


def test_add_global_lock_merges_agents(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    add_skill_to_global_lock(
        "demo",
        source="https://github.com/acme/repo.git",
        source_type="github",
        source_url="https://github.com/acme/repo.git",
        skill_path="skills/demo/SKILL.md",
        skill_folder_hash="hash1",
        agents=["codex"],
        install_mode="symlink",
        source_id="acme/repo",
    )

    add_skill_to_global_lock(
        "demo",
        source="https://github.com/acme/repo.git",
        source_type="github",
        source_url="https://github.com/acme/repo.git",
        skill_path="skills/demo/SKILL.md",
        skill_folder_hash="hash2",
        agents=["claude-code"],
        install_mode="copy",
        source_id="acme/repo",
    )

    lock = read_global_lock()
    entry = lock.skills["demo"]
    assert entry.agents == ["claude-code", "codex"]
    assert entry.install_mode == "copy"


def test_remove_skill_agents_from_global_lock_partial(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    add_skill_to_global_lock(
        "demo",
        source="https://github.com/acme/repo.git",
        source_type="github",
        source_url="https://github.com/acme/repo.git",
        skill_path="skills/demo/SKILL.md",
        skill_folder_hash="hash1",
        agents=["codex", "claude-code"],
        install_mode="symlink",
        source_id="acme/repo",
    )

    changed = remove_skill_agents_from_global_lock("demo", ["codex"])
    assert changed is True

    lock = read_global_lock()
    assert lock.skills["demo"].agents == ["claude-code"]
