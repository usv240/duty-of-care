from __future__ import annotations

import os

from fastapi import FastAPI

from .filters import DISCLAIMER, validate_rendered_text
from .grounding import retrieve_clauses
from .models import ReviewRequest
from .resources import resources_for
from .triggers import detect_triggers, parse_scenes


app = FastAPI(title="Duty of Care API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "healthy",
        "product_surface": "replit_required",
        "integrations": {
            "vertex_search": bool(os.getenv("VERTEX_SEARCH_DATA_STORE")),
            "replit": bool(os.getenv("REPLIT_DEPLOYMENT")),
        },
    }


@app.get("/v1/resources")
def resources(region: str = "US") -> dict[str, object]:
    return {"data": resources_for(region)}


@app.post("/v1/review")
def review(request: ReviewRequest) -> dict[str, object]:
    scenes = {scene.scene_id: scene for scene in parse_scenes(request.screenplay)}
    triggers = detect_triggers(request.screenplay)
    grounded_flags = []
    for scene_id in sorted({trigger.scene_id for trigger in triggers if trigger.scene_id in scenes}):
        relevant = [trigger for trigger in triggers if trigger.scene_id == scene_id]
        clauses = retrieve_clauses(scenes[scene_id], relevant, request.region)
        # No citation means no flag. Deterministic trigger candidates stay visible for
        # audit but are not represented as guidance conflicts.
        if clauses:
            grounded_flags.append({"scene_id": scene_id, "triggers": [item.model_dump() for item in relevant], "clauses": [item.model_dump() for item in clauses]})
    return {
        "data": {
            "grounded_flags": grounded_flags,
            "trigger_candidates": [item.model_dump() for item in triggers],
            "grounding_status": "available" if os.getenv("VERTEX_SEARCH_DATA_STORE") else "not_configured",
            "writer_controls": ["accept", "dismiss", "request_expert_review"],
            "resources": resources_for(request.region),
            "disclaimer": validate_rendered_text(DISCLAIMER),
        }
    }
