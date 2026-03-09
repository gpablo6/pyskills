import httpx

from pyskills.services.find import search_skills_api


class MockResponse:
    def __init__(self, status_code: int, payload) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self):  # noqa: ANN201
        return self._payload


def test_search_skills_api_parses_results(monkeypatch) -> None:
    def fake_get(url: str, params: dict, timeout: float) -> MockResponse:  # noqa: ARG001
        assert url.endswith("/api/search")
        assert params["q"] == "review"
        return MockResponse(
            200,
            {
                "skills": [
                    {
                        "id": "find-skills",
                        "name": "Find Skills",
                        "source": "vercel-labs/skills",
                        "installs": 1450,
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    results = search_skills_api("review")

    assert len(results) == 1
    assert results[0].slug == "find-skills"
    assert results[0].source == "vercel-labs/skills"


def test_search_skills_api_handles_http_errors(monkeypatch) -> None:
    def fake_get(url: str, params: dict, timeout: float):  # noqa: ARG001, ANN201
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "get", fake_get)
    assert search_skills_api("review") == []
