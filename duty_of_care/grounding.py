from __future__ import annotations

import os
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession

from .models import GuidanceClause, Scene, Trigger


class GroundingNotConfigured(RuntimeError):
    pass


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise GroundingNotConfigured(f"{name} is required")
    return value


def _serving_config(data_store: str | None = None) -> str:
    # Some Cloud Run revisions expose the numeric project number through
    # GOOGLE_CLOUD_PROJECT. Agent Search resource names use the project ID.
    project = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or _required("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("VERTEX_SEARCH_LOCATION", "global")
    data_store = data_store or _required("VERTEX_SEARCH_DATA_STORE")
    return (
        f"projects/{project}/locations/{location}/collections/default_collection/"
        f"dataStores/{data_store}/servingConfigs/default_search"
    )


def _as_plain(value: Any) -> Any:
    if hasattr(value, "items"):
        return {str(key): _as_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_as_plain(item) for item in value]
    return value


def _search(query: str, page_size: int) -> list[dict[str, Any]]:
    return _search_store(None, query, page_size)


def _search_store(data_store: str | None, query: str, page_size: int) -> list[dict[str, Any]]:
    """One Agent Search round trip against a named data store (default: the guidance store)."""
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    response = session.post(
        f"https://discoveryengine.googleapis.com/v1/{_serving_config(data_store)}:search",
        json={"query": query, "pageSize": page_size},
        headers={
            "X-Goog-User-Project": os.getenv("GOOGLE_CLOUD_PROJECT_ID")
            or _required("GOOGLE_CLOUD_PROJECT")
        },
        timeout=45,
    )
    if not response.ok:
        try:
            error = response.json().get("error", {})
            category = str(error.get("status", "UNKNOWN"))
            message = str(error.get("message", ""))[:260]
        except ValueError:
            category = "NON_JSON_ERROR"
            message = ""
        raise RuntimeError(
            f"Agent Search HTTP {response.status_code} ({category}): {message}"
        )
    return list(response.json().get("results", []))


SEARCH_WINDOW = 50
MAX_CLAUSES_PER_NOTE = 6


def retrieve_clauses(scene: Scene, triggers: list[Trigger], region: str) -> list[GuidanceClause]:
    """Retrieve candidates from Agent Search, then enforce applicability in code.

    The window covers the whole corpus so applicability filtering in code can
    never be starved by ranking; the top applicable clauses, in Agent Search's
    relevance order, are kept for the note.
    """

    trigger_classes = sorted({item.trigger_class for item in triggers})
    if not trigger_classes:
        return []
    query = (
        f"screen depiction guidance for {', '.join(trigger_classes)}; "
        f"jurisdiction {region.upper()}; scene context {scene.text[:1200]}"
    )
    response = _search(query, SEARCH_WINDOW)
    allowed_regions = {"GLOBAL", region.upper()}
    clauses = _applicable(response, trigger_classes, allowed_regions)
    if not clauses:
        # Semantic ranking on a long scene can leave applicable records outside the
        # window. A second, class-only query keeps retrieval as the sole source of
        # clauses while giving the ranker the terms the corpus is indexed on.
        response = _search(
            f"screen depiction guidance for {', '.join(trigger_classes)}; jurisdiction {region.upper()}",
            SEARCH_WINDOW,
        )
        clauses = _applicable(response, trigger_classes, allowed_regions)
    return clauses


def _applicable(
    response: list[dict[str, Any]], trigger_classes: list[str], allowed_regions: set[str]
) -> list[GuidanceClause]:
    clauses: list[GuidanceClause] = []
    seen: set[str] = set()
    for result in response:
        document = result.get("document", {})
        data = _as_plain(document.get("structData", {}))
        clause_id = str(data.get("clause_id", document.get("id", "")))
        classes = [str(item) for item in data.get("trigger_classes", [])]
        if str(data.get("jurisdiction", "GLOBAL")).upper() not in allowed_regions:
            continue
        if not set(classes).intersection(trigger_classes):
            continue
        if clause_id in seen or not data.get("source_url") or not data.get("clause"):
            continue
        seen.add(clause_id)
        clauses.append(
            GuidanceClause(
                clause_id=clause_id,
                jurisdiction=str(data.get("jurisdiction", "GLOBAL")),
                publisher=str(data["publisher"]),
                document_title=str(data["document_title"]),
                clause=str(data["clause"]),
                source_url=str(data["source_url"]),
                trigger_classes=classes,
                version=str(data.get("version", "")),
                retrieved_at=str(data.get("retrieved_at", "")),
            )
        )
        if len(clauses) >= MAX_CLAUSES_PER_NOTE:
            break
    return clauses


def probe_search() -> dict[str, object]:
    results = _search("help seeking portrayal guidance", 1)
    first = results[0] if results else None
    return {
        "ok": first is not None,
        "document_id": first.get("document", {}).get("id") if first else None,
    }
