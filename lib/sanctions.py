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
    """Match a name against OpenSanctions for AML screening.

    Uses the /match/default endpoint which is purpose-built for entity resolution
    with confidence scores (vs /search which is keyword-based, no scores).

    Queries the name as both Person and Organization since the customer name field
    can hold either a natural person or a legal entity.

    Returns:
        results — list of matched entities, deduped by id, sorted by score desc
        total — number of unique matches returned
        error — present only if the request failed
        api_key_required — True if a 401 was returned (no/invalid key)
    """
    query = (query or "").strip()
    if len(query) < 3:
        return {"results": [], "total": 0}

    api_key = os.getenv("OPENSANCTIONS_API_KEY")
    if not api_key:
        return {"results": [], "total": 0, "api_key_required": True}

    headers = {
        "Authorization": f"ApiKey {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "queries": {
            "person": {
                "schema": "Person",
                "properties": {"name": [query]},
            },
            "org": {
                "schema": "Organization",
                "properties": {"name": [query]},
            },
        }
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{OPENSANCTIONS_BASE}/match/default",
                params={"limit": limit},
                json=payload,
                headers=headers,
            )

        if response.status_code == 401:
            return {"results": [], "total": 0, "api_key_required": True}
        response.raise_for_status()
        data = response.json()

        # Merge results from both Person and Organization queries
        unique: dict[str, dict] = {}
        for query_response in data.get("responses", {}).values():
            for r in query_response.get("results", []):
                rid = r.get("id")
                if not rid:
                    continue
                # Keep the highest-scoring result for each unique entity
                if rid not in unique or (r.get("score") or 0) > (unique[rid].get("score") or 0):
                    unique[rid] = r

        results = sorted(
            unique.values(),
            key=lambda x: x.get("score") or 0,
            reverse=True,
        )[:limit]

        return {"results": results, "total": len(results)}

    except httpx.HTTPError as e:
        return {"results": [], "total": 0, "error": str(e)}


def classify_match(score: float) -> str:
    """Return a risk classification for a match score (0.0–1.0)."""
    if score >= 0.85:
        return "high"
    if score >= 0.65:
        return "medium"
    return "low"


def summarize_entity(entity: dict[str, Any]) -> dict[str, Any]:
    """Pull out the fields most useful for a quick analyst review."""
    props = entity.get("properties", {}) or {}
    return {
        "caption": entity.get("caption") or "Unknown",
        "schema": entity.get("schema") or "Entity",
        "datasets": ", ".join(entity.get("datasets", [])[:4]) or "—",
        "score": float(entity.get("score") or 0.0),
        "match": bool(entity.get("match")),
        "target": bool(entity.get("target")),
        "topics": ", ".join(props.get("topics", [])[:4]) or "—",
        "country": ", ".join(props.get("country", [])[:3]) or "—",
        "url": f"https://www.opensanctions.org/entities/{entity.get('id', '')}/" if entity.get("id") else "",
    }
