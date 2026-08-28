from __future__ import annotations

import asyncio
import json
import os
import time
from hashlib import sha256
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai

from .adk_app import explain_grounded_flag
from .filters import DISCLAIMER, validate_rendered_text
from .grounding import GroundingNotConfigured, probe_search, retrieve_clauses
from .models import ReviewRequest
from .resources import resources_for
from .triggers import detect_triggers, parse_scenes


app = FastAPI(title="Duty of Care API", version="0.2.0")
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "app" / "web"
CORPUS = ROOT / "guidance" / "corpus.json"
PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv(
    "GOOGLE_CLOUD_PROJECT", "agentic-fleet-2026"
)
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_HEALTH: dict[str, object] = {"checked": 0.0, "value": None}


def _vertex_probe() -> dict[str, object]:
    with genai.Client(vertexai=True, project=PROJECT, location=LOCATION) as client:
        response = client.models.generate_content(model=MODEL, contents="Reply with exactly OK.")
    return {"ok": bool(response.text), "model": MODEL}


async def _live_integrations() -> dict[str, object]:
    now = time.monotonic()
    if _HEALTH["value"] and now - float(_HEALTH["checked"]) < 60:
        return dict(_HEALTH["value"])
    vertex, search = await asyncio.gather(
        asyncio.to_thread(_vertex_probe),
        asyncio.to_thread(probe_search),
        return_exceptions=True,
    )
    value = {
        "google_vertex": vertex if isinstance(vertex, dict) else {"ok": False, "detail": type(vertex).__name__},
        "agent_search": search if isinstance(search, dict) else {"ok": False, "detail": str(search)[:360]},
        "google_adk": {"ok": not isinstance(vertex, Exception) and not isinstance(search, Exception)},
        "replit": {
            "ok": bool(os.getenv("REPL_ID") or os.getenv("REPLIT_DEPLOYMENT")),
            "host": os.getenv("REPLIT_DEV_DOMAIN") or os.getenv("REPLIT_DOMAINS") or None,
        },
    }
    _HEALTH.update(checked=now, value=value)
    return value


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/health")
async def health() -> dict[str, object]:
    integrations = await _live_integrations()
    return {
        "status": "healthy",
        "integrations": integrations,
        "agent_runtime_ready": bool(
            integrations["google_vertex"]["ok"] and integrations["agent_search"]["ok"]
        ),
        "product_surface": "replit" if integrations["replit"]["ok"] else "cloud_run_fallback",
    }


@app.get("/v1/resources")
def resources(region: str = "US") -> dict[str, object]:
    return {"data": resources_for(region), "disclaimer": validate_rendered_text(DISCLAIMER)}


@app.get("/v1/guidance")
def guidance() -> dict[str, object]:
    records = json.loads(CORPUS.read_text("utf-8"))
    return {
        "data": {
            "retrieval": "google_agent_search",
            "documents": records,
            "count": len(records),
        },
        "disclaimer": validate_rendered_text(DISCLAIMER),
    }


@app.get("/v1/samples")
def samples() -> dict[str, object]:
    return {
        "data": {
            "flagged": "INT. BEDROOM - NIGHT\nMARA describes an exact amount and calls suicide the only way out.",
            "not_flagged": "INT. KITCHEN - DAWN\nMARA names her suicidal thoughts. A friend stays, calls for support, and they plan coping steps. END CARD: Call or text 988; help is available.",
            "provenance": "self-authored CC0 demonstration scenes",
        },
        "disclaimer": validate_rendered_text(DISCLAIMER),
    }


@app.post("/v1/review")
async def review(request: ReviewRequest) -> dict[str, object]:
    scenes = {scene.scene_id: scene for scene in parse_scenes(request.screenplay)}
    triggers = detect_triggers(request.screenplay)
    grounded_flags: list[dict[str, object]] = []
    configured = bool(os.getenv("VERTEX_SEARCH_DATA_STORE"))
    if configured:
        scene_ids = sorted({item.scene_id for item in triggers if item.scene_id in scenes})[:10]
        for scene_id in scene_ids:
            relevant = [item for item in triggers if item.scene_id == scene_id]
            try:
                clauses = await asyncio.to_thread(
                    retrieve_clauses, scenes[scene_id], relevant, request.region
                )
            except GroundingNotConfigured as exc:
                raise HTTPException(503, detail={"code": "grounding_not_configured", "message": str(exc)}) from exc
            except Exception as exc:
                raise HTTPException(
                    502,
                    detail={
                        "code": "grounding_failed",
                        "message": f"Agent Search failed closed ({type(exc).__name__}); no guidance flag was fabricated.",
                    },
                ) from exc
            if not clauses:
                continue
            try:
                explanation = await explain_grounded_flag(
                    scenes[scene_id], relevant, clauses, operator_id="public_writer"
                )
            except Exception as exc:
                raise HTTPException(
                    502,
                    detail={
                        "code": "agent_review_failed",
                        "message": f"The ADK review failed closed ({type(exc).__name__}); no explanation was fabricated.",
                    },
                ) from exc
            grounded_flags.append(
                {
                    "flag_id": "flag_" + sha256(
                        f"{scene_id}:{','.join(item.clause_id for item in clauses)}".encode()
                    ).hexdigest()[:16],
                    "scene_id": scene_id,
                    "heading": scenes[scene_id].heading,
                    "triggers": [item.model_dump() for item in relevant],
                    "clauses": [item.model_dump() for item in clauses],
                    "agent": explanation,
                    "state": "open",
                }
            )
    return {
        "data": {
            "scenes": [scene.model_dump() for scene in scenes.values()],
            "grounded_flags": grounded_flags,
            "trigger_candidates": [item.model_dump() for item in triggers],
            "grounding_status": "available" if configured else "not_configured",
            "writer_controls": ["accept", "dismiss", "request_expert_review"],
            "resources": resources_for(request.region),
            "disclaimer": validate_rendered_text(DISCLAIMER),
            "decision_owner": "writer",
            "overall_score": None,
        }
    }


app.mount("/static", StaticFiles(directory=WEB), name="static")
