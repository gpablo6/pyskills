from pathlib import Path

import pytest

from pyskills.models import AgentConfig
from pyskills.models import Skill
from pyskills.services import install_skill_for_agent
from pyskills.services import installer as installer_module


def test_install_skill_copy_mode(tmp_path: Path) -> None:
    source_dir = tmp_path / "source-skill"
    source_dir.mkdir()
    (source_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: test\n---\n",
        encoding="utf-8",
    )

    skill = Skill(name="demo", description="test", path=source_dir)

    result = install_skill_for_agent(skill, "codex", cwd=tmp_path, mode="copy")

    assert result.success
    assert result.path.exists()
    assert (result.path / "SKILL.md").exists()


def test_install_skill_symlink_mode(tmp_path: Path) -> None:
    source_dir = tmp_path / "source-skill"
    source_dir.mkdir()
    (source_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: test\n---\n",
        encoding="utf-8",
    )
    skill = Skill(name="demo", description="test", path=source_dir)

    result = install_skill_for_agent(
        skill,
        "claude-code",
        cwd=tmp_path,
        mode="symlink",
    )

    assert result.success
    assert result.path.exists()
    assert result.path.is_symlink() or (result.path / "SKILL.md").exists()
    assert result.canonical_path is not None


def test_install_skill_symlink_fallback_to_copy(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "source-skill"
    source_dir.mkdir()
    (source_dir / "SKILL.md").write_text(
        "---\nname: demo\ndescription: test\n---\n",
        encoding="utf-8",
    )
    skill = Skill(name="demo", description="test", path=source_dir)

    def fail_symlink(self, target, target_is_directory=False):  # noqa: ANN001, ANN201, ARG001
        raise OSError("symlink blocked")

    monkeypatch.setattr(Path, "symlink_to", fail_symlink)

    result = install_skill_for_agent(
        skill,
        "claude-code",
        cwd=tmp_path,
        mode="symlink",
    )

    assert result.success
    assert result.symlink_failed is True
    assert (result.path / "SKILL.md").exists()


def test_get_agent_base_dir_global_unsupported_raises(
    monkeypatch,
    tmp_path: Path,
) -> None:
    test_agents = {
        "x": AgentConfig(
            name="x",
            display_name="X",
            skills_dir=Path(".x/skills"),
            global_skills_dir=None,
        )
    }
    monkeypatch.setattr(installer_module, "AGENTS", test_agents)
    monkeypatch.setattr(
        installer_module,
        "is_universal_agent",
        lambda agent_name: False,  # noqa: ARG005
    )

    with pytest.raises(ValueError):
        installer_module.get_agent_base_dir(
            "x",
            global_install=True,
            cwd=tmp_path,
        )
