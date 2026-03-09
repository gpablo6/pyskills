"""Agent registry and detection services."""

from __future__ import annotations

from pathlib import Path

from pyskills.models import AgentConfig


AGENTS: dict[str, AgentConfig] = {
    "codex": AgentConfig(
        name="codex",
        display_name="Codex",
        skills_dir=Path(".agents/skills"),
        global_skills_dir=Path.home() / ".codex/skills",
    ),
    "claude-code": AgentConfig(
        name="claude-code",
        display_name="Claude Code",
        skills_dir=Path(".claude/skills"),
        global_skills_dir=Path.home() / ".claude/skills",
    ),
    "cursor": AgentConfig(
        name="cursor",
        display_name="Cursor",
        skills_dir=Path(".agents/skills"),
        global_skills_dir=Path.home() / ".cursor/skills",
    ),
    "universal": AgentConfig(
        name="universal",
        display_name="Universal",
        skills_dir=Path(".agents/skills"),
        global_skills_dir=Path.home() / ".config/agents/skills",
        show_in_universal_list=False,
    ),
}


def detect_installed_agents(cwd: Path | None = None) -> list[str]:
    """Detect agents likely installed on the current machine.

    Parameters
    ----------
    cwd : pathlib.Path or None, optional
        Project root used to check project-scoped directories.

    Returns
    -------
    list of str
        Agent identifiers that appear installed by directory presence checks.
    """

    root = cwd or Path.cwd()
    installed: list[str] = []

    for name, cfg in AGENTS.items():
        project_dir = root / cfg.skills_dir.parent
        if project_dir.exists() or (
            cfg.global_skills_dir and cfg.global_skills_dir.parent.exists()
        ):
            installed.append(name)

    return installed


def get_universal_agents() -> list[str]:
    """Return agents that share the universal ``.agents/skills`` directory.

    Returns
    -------
    list of str
        Agent identifiers configured for universal installs.
    """

    return [
        name
        for name, cfg in AGENTS.items()
        if cfg.skills_dir.as_posix() == ".agents/skills"
        and cfg.show_in_universal_list
    ]


def is_universal_agent(agent_name: str) -> bool:
    """Check whether an agent uses the universal skill directory.

    Parameters
    ----------
    agent_name : str
        Agent identifier.

    Returns
    -------
    bool
        ``True`` when the agent resolves to ``.agents/skills``.
    """

    cfg = AGENTS[agent_name]
    return cfg.skills_dir.as_posix() == ".agents/skills"
