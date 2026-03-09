from pathlib import Path

from pyskills.models import AgentConfig
from pyskills.services import agents as agents_module


def test_universal_agent_helpers() -> None:
    values = agents_module.get_universal_agents()
    assert "codex" in values
    assert "cursor" in values
    assert agents_module.is_universal_agent("codex")
    assert not agents_module.is_universal_agent("claude-code")


def test_detect_installed_agents_project_dirs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    test_agents = {
        "a": AgentConfig(
            name="a",
            display_name="A",
            skills_dir=Path(".a/skills"),
            global_skills_dir=None,
        ),
        "b": AgentConfig(
            name="b",
            display_name="B",
            skills_dir=Path(".b/skills"),
            global_skills_dir=None,
        ),
    }
    monkeypatch.setattr(agents_module, "AGENTS", test_agents)

    (tmp_path / ".a").mkdir(parents=True)

    detected = agents_module.detect_installed_agents(cwd=tmp_path)
    assert detected == ["a"]
