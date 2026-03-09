from pathlib import Path

import httpx
import pytest

from pyskills.services.well_known import (
    WellKnownError,
    materialize_well_known_source,
)


class MockResponse:
    def __init__(
        self,
        status_code: int,
        json_data=None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text

    def json(self):  # noqa: ANN201
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data


def test_materialize_well_known_source_downloads_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_get(url: str, timeout: float) -> MockResponse:  # noqa: ARG001
        if url.endswith("/.well-known/skills/index.json"):
            return MockResponse(
                200,
                json_data={
                    "skills": [
                        {
                            "name": "demo",
                            "description": "Demo skill",
                            "files": ["SKILL.md", "guide.txt"],
                        }
                    ]
                },
            )

        if url.endswith("/demo/SKILL.md"):
            return MockResponse(
                200,
                text="---\nname: demo\ndescription: Demo\n---\n",
            )

        if url.endswith("/demo/guide.txt"):
            return MockResponse(200, text="hello")

        return MockResponse(404)

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(
        "tempfile.mkdtemp",
        lambda prefix: str(tmp_path / f"{prefix}x"),
    )

    out_dir = materialize_well_known_source("https://example.com")

    assert (out_dir / "demo" / "SKILL.md").exists()
    guide = (out_dir / "demo" / "guide.txt").read_text(
        encoding="utf-8"
    )
    assert guide == "hello"


def test_materialize_well_known_source_rejects_missing_skill_md(
    monkeypatch,
) -> None:
    def fake_get(url: str, timeout: float) -> MockResponse:  # noqa: ARG001
        if url.endswith("/.well-known/skills/index.json"):
            return MockResponse(
                200,
                json_data={
                    "skills": [
                        {
                            "name": "bad",
                            "description": "Bad",
                            "files": ["README.md"],
                        }
                    ]
                },
            )
        return MockResponse(404)

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(WellKnownError):
        materialize_well_known_source("https://example.com")
