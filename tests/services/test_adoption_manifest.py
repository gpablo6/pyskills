from pathlib import Path

from pyskills.services.adoption_manifest import undo_adoption
from pyskills.services.consolidation import apply_adoption


def _write_skill(path: Path, body: str = "") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"---\nname: demo\ndescription: demo\n---\n{body}\n",
        encoding="utf-8",
    )


def test_undo_adoption_restores_backup_and_removes_created(
    tmp_path: Path,
) -> None:
    original = tmp_path / ".claude/skills/demo"
    _write_skill(original, body="user-content")

    _, apply_result = apply_adoption(global_install=False, cwd=tmp_path)
    assert apply_result.manifest_path is not None

    canonical = tmp_path / ".agents/skills/demo"
    assert canonical.exists()

    undo_result = undo_adoption(manifest_path=apply_result.manifest_path)

    restored_content = (original / "SKILL.md").read_text(encoding="utf-8")
    assert "user-content" in restored_content
    assert undo_result.restored_paths >= 1
    assert undo_result.removed_created_paths >= 1
    assert not canonical.exists()
