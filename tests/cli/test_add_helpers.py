import importlib
from pathlib import Path

from pyskills.models import ParsedSource, Skill, SourceType


def test_add_lock_source_id_and_path_helpers(tmp_path: Path) -> None:
    add_module = importlib.import_module("pyskills.cli.commands.add")

    parsed_github = ParsedSource(
        type=SourceType.GITHUB,
        url="https://github.com/acme/skills.git",
    )
    parsed_well_known = ParsedSource(
        type=SourceType.WELL_KNOWN,
        url="https://skills.sh",
    )

    assert (
        add_module._lock_source_id(
            parsed_github,
            "https://github.com/acme/skills.git",
        )
        == "acme/skills"
    )
    assert (
        add_module._lock_source_id(
            parsed_well_known,
            "https://skills.sh/catalog",
        )
        == "skills.sh/catalog"
    )

    root = tmp_path / "repo"
    skill_path = root / "skills" / "demo"
    skill_path.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir(parents=True)

    assert add_module._skill_path_for_lock(root, root) == "SKILL.md"
    assert (
        add_module._skill_path_for_lock(skill_path, root)
        == "skills/demo/SKILL.md"
    )
    assert add_module._skill_path_for_lock(outside, root) == "SKILL.md"


def test_add_update_lock_entries_global_github_uses_latest_hash(
    monkeypatch,
    tmp_path: Path,
) -> None:
    add_module = importlib.import_module("pyskills.cli.commands.add")

    skill_path = tmp_path / "repo" / "skills" / "demo"
    skill_path.mkdir(parents=True)
    skill = Skill(
        name="demo",
        description="demo",
        path=skill_path,
    )
    parsed = ParsedSource(
        type=SourceType.GITHUB,
        url="https://github.com/acme/skills.git",
    )
    captured: list[dict] = []

    monkeypatch.setattr(
        add_module,
        "compute_skill_folder_hash",
        lambda path: "old-hash",  # noqa: ARG005
    )
    monkeypatch.setattr(
        add_module,
        "parse_github_owner_repo",
        lambda value: "acme/skills",  # noqa: ARG005
    )
    monkeypatch.setattr(
        add_module,
        "fetch_github_skill_folder_hash",
        lambda owner_repo, skill_path: "new-hash",  # noqa: ARG005
    )
    monkeypatch.setattr(
        add_module,
        "add_skill_to_global_lock",
        lambda *args, **kwargs: captured.append(kwargs),
    )

    add_module._update_lock_entries(
        selected=[skill],
        parsed=parsed,
        global_install=True,
        source_root=tmp_path / "repo",
        target_agents=["codex"],
        install_mode="symlink",
    )

    assert captured
    assert captured[0]["skill_folder_hash"] == "new-hash"
