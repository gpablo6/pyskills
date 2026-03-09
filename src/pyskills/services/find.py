"""Skills search services."""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class SearchSkill:
    """Represents one search result skill."""

    name: str
    slug: str
    source: str
    installs: int


def search_skills_api(
    query: str,
    *,
    limit: int = 10,
    base_url: str = "https://skills.sh",
) -> list[SearchSkill]:
    """Search skills via remote API.

    Parameters
    ----------
    query : str
        Search terms.
    limit : int, optional
        Maximum number of results.
    base_url : str, optional
        Base API host URL.

    Returns
    -------
    list of SearchSkill
        Parsed search results. Returns empty list on request/parse failures.
    """

    if not query.strip():
        return []

    url = f"{base_url.rstrip('/')}/api/search"

    try:
        response = httpx.get(
            url,
            params={"q": query, "limit": str(limit)},
            timeout=8.0,
        )
    except httpx.HTTPError:
        return []

    if response.status_code >= 400:
        return []

    try:
        payload = response.json()
    except ValueError:
        return []

    skills = payload.get("skills") if isinstance(payload, dict) else None
    if not isinstance(skills, list):
        return []

    results: list[SearchSkill] = []
    for item in skills:
        if not isinstance(item, dict):
            continue

        name = item.get("name")
        slug = item.get("id") or item.get("slug")
        source = item.get("source")
        installs = item.get("installs")

        if not isinstance(name, str) or not name:
            continue
        if not isinstance(slug, str) or not slug:
            continue
        if not isinstance(source, str):
            source = ""
        if not isinstance(installs, int):
            installs = 0

        results.append(
            SearchSkill(
                name=name,
                slug=slug,
                source=source,
                installs=installs,
            )
        )

    return results
