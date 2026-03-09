from pathlib import Path

import pytest

from pyskills.models import SourceType
from pyskills.services import parse_source, sanitize_subpath


def test_parse_owner_repo_with_skill_filter() -> None:
    parsed = parse_source("vercel-labs/skills@find-skills")
    assert parsed.type == SourceType.GITHUB
    assert parsed.url == "https://github.com/vercel-labs/skills.git"
    assert parsed.skill_filter == "find-skills"


def test_parse_local_path(tmp_path: Path) -> None:
    parsed = parse_source(str(tmp_path))
    assert parsed.type == SourceType.LOCAL
    assert parsed.local_path == tmp_path.resolve()


def test_sanitize_subpath_rejects_traversal() -> None:
    with pytest.raises(ValueError):
        sanitize_subpath("skills/../secret")


def test_parse_well_known_skill_url_sets_skill_filter() -> None:
    parsed = parse_source("https://example.com/.well-known/skills/review")
    assert parsed.type == SourceType.WELL_KNOWN
    assert parsed.skill_filter == "review"
