from pathlib import Path

from pyskills.services.consolidation import (
    apply_adoption,
    build_adoption_report,
    filter_adoption_report,
)


def _write_skill(
    path: Path,
    name: str,
    description: str,
    body: str = "",
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n{body}\n",
        encoding="utf-8",
    )


def test_adoption_marks_user_skill_needing_adoption(tmp_path: Path) -> None:
    _write_skill(tmp_path / ".claude/skills/demo", "demo", "demo")

    report = build_adoption_report(global_install=False, cwd=tmp_path)
    demo = next(item for item in report.items if item.name == "demo")

    assert demo.ownership == "user"
    assert demo.status == "needs-adoption"


def test_adoption_detects_conflict_same_name_diff_content(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path / ".agents/skills/demo", "demo", "demo", body="a")
    _write_skill(tmp_path / ".claude/skills/demo", "demo", "demo", body="b")

    report = build_adoption_report(global_install=False, cwd=tmp_path)
    demo = next(item for item in report.items if item.name == "demo")

    assert demo.status == "conflict"


def test_adoption_marks_external_from_local_lock(tmp_path: Path) -> None:
    _write_skill(tmp_path / ".claude/skills/demo", "demo", "demo")
    (tmp_path / "skills-lock.json").write_text(
        '{"version":1,"skills":{"demo":{"source":"x","source_type":"github","computed_hash":"abc"}}}',
        encoding="utf-8",
    )

    report = build_adoption_report(global_install=False, cwd=tmp_path)
    demo = next(item for item in report.items if item.name == "demo")

    assert demo.ownership == "external"


def test_apply_adoption_creates_canonical_and_backup(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path / ".claude/skills/demo", "demo", "demo")

    _, result = apply_adoption(
        global_install=False,
        cwd=tmp_path,
    )

    canonical_skill = tmp_path / ".agents/skills/demo/SKILL.md"
    assert canonical_skill.exists()

    backups = list((tmp_path / ".claude/skills").glob("demo.bak-*"))
    assert backups
    assert result.backup_entries
    assert result.manifest_path is not None


def test_apply_conflict_keep_existing_skips_changes(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path / ".agents/skills/demo", "demo", "demo", body="a")
    _write_skill(tmp_path / ".claude/skills/demo", "demo", "demo", body="b")

    _, result = apply_adoption(
        global_install=False,
        cwd=tmp_path,
        conflict_policy="keep-existing",
    )

    content = (tmp_path / ".claude/skills/demo/SKILL.md").read_text(
        encoding="utf-8",
    )
    assert "b" in content
    assert result.skipped_groups == 1
    assert not result.backup_entries


def test_filter_adoption_report_keeps_selected_skill(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path / ".claude/skills/demo", "demo", "demo")
    _write_skill(tmp_path / ".claude/skills/alpha", "alpha", "alpha")

    report = build_adoption_report(global_install=False, cwd=tmp_path)
    filtered = filter_adoption_report(report, ["demo"], strict=True)

    assert filtered.total_skills == 1
    assert filtered.items[0].name == "demo"


def test_apply_adoption_only_selected_skill(tmp_path: Path) -> None:
    _write_skill(tmp_path / ".claude/skills/demo", "demo", "demo")
    _write_skill(tmp_path / ".claude/skills/alpha", "alpha", "alpha")

    _, result = apply_adoption(
        global_install=False,
        cwd=tmp_path,
        skill_names=["demo"],
    )

    assert (tmp_path / ".agents/skills/demo").exists()
    assert not (tmp_path / ".agents/skills/alpha").exists()
    assert result.manifest_path is not None


def test_apply_conflict_use_canonical_replaces_duplicate(
    tmp_path: Path,
) -> None:
    _write_skill(tmp_path / ".agents/skills/demo", "demo", "demo", body="a")
    _write_skill(tmp_path / ".claude/skills/demo", "demo", "demo", body="b")

    _, result = apply_adoption(
        global_install=False,
        cwd=tmp_path,
        conflict_policy="use-canonical",
    )

    claude_path = tmp_path / ".claude/skills/demo"
    assert claude_path.exists()
    assert claude_path.is_symlink() or (claude_path / "SKILL.md").exists()
    assert result.skipped_groups == 0
    assert result.backup_entries
