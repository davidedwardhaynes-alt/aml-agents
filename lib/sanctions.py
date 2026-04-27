"""OpenSanctions integration — sanctions, PEP, and watchlist screening.

OpenSanctions aggregates 200+ public sanctions, PEP, and watchlist sources
including OFAC SDN, UN consolidated, EU consolidated, UK HMT, MAS targeted
financial sanctions, AUSTRAC, and HKMA / SFC enforcement lists.

Free tier: 100 requests/day. Higher quota requires an API key (set
OPENSANCTIONS_API_KEY in .env). For v0 design-partner demos the free tier
is sufficient.
"""

import os
from typing import Any

import httpx

OPENSANCTIONS_BASE = "https://api.opensanctions.org"


def search_sanctions(query: str, limit: int = 5) -> dict[str, Any]:
    """Search OpenSanctions for entities matching a name query.

    Returns:
        results — list of matched entities (caption, score, schema, datasets, properties)
        total — total matches in the corpus
        error — present only if the request failed
        api_key_required — True if a 401 was returned (no/invalid key)
    """
    query = (query or "").strip()
    if len(query) < 3:
        return {"results": [], "total": 0}

    api_key = os.getenv("OPENSANCTIONS_API_KEY")
    if not api_key:
        return {"results": [], "total": 0, "api_key_required": True}

    headers = {"Authorization": f"ApiKey {api_key}"}

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{OPENSANCTIONS_BASE}/search/default",
                params={"q": query, "limit": limit},
                headers=headers,
            )

        if response.status_code == 401:
            return {"results": [], "total": 0, "api_key_required": True}
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        total_field = data.get("total", {})
        if isinstance(total_field, dict):
            total_count = total_field.get("value", len(results))
        else:
            total_count = int(total_field) if total_field else len(results)

        return {"results": results, "total": total_count}

    except httpx.HTTPError as e:
        return {"results": [], "total": 0, "error": str(e)}


def classify_match(score: float) -> str:
    """Return a risk classification for a match score (0.0–1.0)."""
    if score >= 0.85:
        return "high"
    if score >= 0.65:
        return "medium"
    return "low"


def summarize_entity(entity: dict[str, Any]) -> dict[str, str]:
    """Pull out the fields most useful for a quick analyst review."""
    props = entity.get("properties", {}) or {}
    return {
        "caption": entity.get("caption") or "Unknown",
        "schema": entity.get("schema") or "Entity",
        "datasets": ", ".join(entity.get("datasets", [])[:4]) or "—",
        "score": float(entity.get("score") or 0.0),
        "topics": ", ".join(props.get("topics", [])[:3]) or "—",
        "country": ", ".join(props.get("country", [])[:3]) or "—",
        "url": f"https://www.opensanctions.org/entities/{entity.get('id', '')}/" if entity.get("id") else "",
    }
