from __future__ import annotations

import os

from .models import GuidanceClause, Scene, Trigger


def retrieve_clauses(scene: Scene, triggers: list[Trigger], region: str) -> list[GuidanceClause]:
    """Fail closed until a real Vertex AI Search data store is configured.

    Candidate triggers are not promoted to guidance conflicts without a retrieved,
    source-linked clause. No model-memory fallback is permitted.
    """
    if not os.getenv("VERTEX_SEARCH_DATA_STORE"):
        return []
    raise RuntimeError("Vertex AI Search adapter must be configured with the approved guidance corpus before review is enabled")
