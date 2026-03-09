from pathlib import Path

from pyskills.services import discover_skills


def test_discover_skills_finds_skill_md(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: test skill\n---\n\n# Demo\n",
        encoding="utf-8",
    )

    found = discover_skills(tmp_path)
    assert len(found) == 1
    assert found[0].name == "demo"
