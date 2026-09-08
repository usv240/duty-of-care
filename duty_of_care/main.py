"""Duty of Care: guidance-grounded pre-review for screenwriters.

Three layers, in order, on every review:

1. Deterministic triggers (pure code) select candidate scenes and show the
   exact phrase and rule.
2. Google Agent Search retrieves applicable, source-linked clauses; a Google
   ADK agent on Gemini explains only those clauses and must self-check its
   alternative through the hard filter. No clause means no flag.
3. The writer decides. Nothing is blocked, nothing is scored.

The same app serves the Cloud Run Google backend and the Replit product
surface. Every response carries `data.disclaimer`; every review carries `meta`
with the gate thresholds that were evaluated, so an integrator sees why a note
exists without trusting prose.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import time
from hashlib import sha256
from importlib import metadata
from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from pydantic import BaseModel, Field, model_validator

from . import apikeys, evidence, model_armor, replit_platform, telemetry
from .adk_app import agent_engine_resource, explain_grounded_flag
from .eval import run_benchmark
from .filters import DISCLAIMER, validate_rendered_text
from .grounding import GroundingNotConfigured, probe_search, retrieve_clauses
from .models import ReviewRequest
from .presets import DOWNLOAD_FORMATS, all_presets, download_payload, get_preset
from .ratelimit import SlidingWindow
from .report import render_markdown
from .resources import REGIONS, resources_for
from .stack import build_stack
from .triggers import DOCUMENT_SCENE_ID, detect_triggers, document_scene, parse_scenes

app = FastAPI(
    title="Duty of Care API",
    version="0.3.0",
    description=(
        "Guidance-grounded pre-review for screenwriters depicting suicide, self-harm, or "
        "addiction. Deterministic triggers select candidates, Google Agent Search retrieves "
        "source-linked clauses, a Google ADK agent explains them, and the writer decides. "
        "Every endpoint works without a key; a key only raises limits."
    ),
)
ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "app" / "web"
CORPUS = ROOT / "guidance" / "corpus.json"
PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv(
    "GOOGLE_CLOUD_PROJECT", "agentic-fleet-2026"
)
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_HEALTH: dict[str, object] = {"checked": 0.0, "value": None}
_LIMITER = SlidingWindow(window_seconds=60)
BASE_LIMITS = {"review": 6, "keys": 10, "exports": 10, "decisions": 30}
_LAST_AGENT_RUNTIME: dict[str, str | None] = {"runtime": None, "model_armor": None}
PAGES = {"/": "index.html", "/presets": "presets.html", "/developers": "developers.html", "/stack": "stack.html", "/evidence": "evidence.html"}


def _version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except Exception:
        return None


def _request_id() -> str:
    return "req_" + secrets.token_hex(8)


def _fail(status: int, code: str, message: str, fix: str, *, headers: dict[str, str] | None = None) -> HTTPException:
    return HTTPException(
        status, detail={"code": code, "message": message, "fix": fix}, headers=headers
    )


@app.exception_handler(HTTPException)
async def _http_error(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "request_error", "message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "ok": False,
            "error": {
                "code": detail.get("code", "request_error"),
                "message": detail.get("message", ""),
                "fix": detail.get("fix", "See /docs for the request shape."),
                "docs": "/docs",
            },
            # Kept for older clients that read FastAPI's default shape.
            "detail": detail,
            "meta": {"request_id": _request_id()},
        },
    )


@app.exception_handler(RequestValidationError)
async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "ok": False,
            "error": {
                "code": "validation_error",
                "message": "The request body did not match the schema.",
                "fix": "Send JSON with a non-empty screenplay (at most 250,000 characters) or a preset_id, plus an optional region.",
                "docs": "/docs",
                "details": json.loads(json.dumps(exc.errors(), default=str)),
            },
            "meta": {"request_id": _request_id()},
        },
    )


def _identity(request: Request) -> apikeys.ApiKeyIdentity:
    try:
        return apikeys.identify(
            request.headers.get("authorization"), request.headers.get("x-api-key")
        )
    except apikeys.ApiKeyError as exc:
        raise _fail(
            401,
            "invalid_api_key",
            str(exc),
            "POST /v1/keys to mint a key, or send no credential to use the anonymous tier.",
        ) from exc


def _limited(request: Request, route: str) -> apikeys.ApiKeyIdentity:
    identity = _identity(request)
    caller = identity.key_id or (request.client.host if request.client else "unknown")
    limit = BASE_LIMITS[route] * apikeys.TIER_MULTIPLIER[identity.tier]
    decision = _LIMITER.check(f"{route}:{caller}", limit)
    if not decision.allowed:
        raise _fail(
            429,
            "rate_limited",
            f"{route} allows {limit} requests per minute for this caller.",
            "Wait and retry, or POST /v1/keys for a key with "
            f"{apikeys.TIER_MULTIPLIER[apikeys.KEYED_TIER]}x this limit.",
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )
    return identity


def _vertex_probe() -> dict[str, object]:
    with genai.Client(vertexai=True, project=PROJECT, location=LOCATION) as client:
        response = client.models.generate_content(model=MODEL, contents="Reply with exactly OK.")
    return {"ok": bool(response.text), "model": MODEL}


async def _live_integrations() -> dict[str, Any]:
    now = time.monotonic()
    if _HEALTH["value"] and now - float(_HEALTH["checked"]) < 60:
        return dict(_HEALTH["value"])  # type: ignore[arg-type]
    runtime = replit_platform.runtime()
    if _backend_url():
        try:
            remote = (await asyncio.to_thread(_fetch_backend_json, "/health/integrations"))["data"]["integrations"]
            google = {key: {**dict(remote.get(key, {"ok": False})), "via": "backend"} for key in ("google_vertex", "agent_search", "google_adk")}
            backend = {"ok": True, "url": _backend_url()}
        except Exception as exc:  # noqa: BLE001 - reported, never hidden
            google = {key: {"ok": False, "detail": f"backend unreachable ({type(exc).__name__})", "via": "backend"} for key in ("google_vertex", "agent_search", "google_adk")}
            backend = {"ok": False, "url": _backend_url()}
        value = {
            **google,
            "api_keys": {"ok": apikeys.configured()},
            "replit": {"ok": runtime["on_replit"], "host": runtime["domains"], "deployment": runtime["deployment"]},
            "backend": backend,
        }
        _HEALTH.update(checked=now, value=value)
        return value
    vertex, search = await asyncio.gather(
        asyncio.to_thread(_vertex_probe),
        asyncio.to_thread(probe_search),
        return_exceptions=True,
    )
    value = {
        "google_vertex": vertex if isinstance(vertex, dict) else {"ok": False, "detail": type(vertex).__name__},
        "agent_search": search if isinstance(search, dict) else {"ok": False, "detail": str(search)[:360]},
        "google_adk": {
            "ok": not isinstance(vertex, Exception) and not isinstance(search, Exception),
            "version": _version("google-adk"),
        },
        "api_keys": {"ok": apikeys.configured()},
        "replit": {"ok": runtime["on_replit"], "host": runtime["domains"], "deployment": runtime["deployment"]},
    }
    _HEALTH.update(checked=now, value=value)
    return value


def _corpus_version() -> str:
    return replit_platform.corpus_version(CORPUS)


def _backend_url() -> str | None:
    """The Google backend this host proxies to, when this host has no Google credentials.

    On Replit the Google services are answered by Cloud Run, so health and stack
    for the Google group are read from the backend and labelled as such; the
    Replit group is always computed locally, because only this process knows it.
    """
    url = os.getenv("DUTY_OF_CARE_BACKEND_URL")
    if url and not os.getenv("VERTEX_SEARCH_DATA_STORE"):
        return url.rstrip("/")
    return None


def _fetch_backend_json(path: str) -> dict[str, Any]:
    import urllib.request

    with urllib.request.urlopen(f"{_backend_url()}{path}", timeout=90) as response:  # noqa: S310 - fixed, allowlisted origin
        return json.loads(response.read().decode("utf-8"))


# ------------------------------------------------------------------ pages ----


for _route, _file in PAGES.items():

    def _page(file: str = _file) -> FileResponse:
        return FileResponse(WEB / file)

    app.get(_route, include_in_schema=False)(_page)


# ----------------------------------------------------------------- health ----


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
        "replit_platform": replit_platform.status(),
        "corpus_version": _corpus_version(),
    }


@app.get("/health/integrations")
async def health_integrations() -> dict[str, object]:
    return {"ok": True, "data": {"integrations": await _live_integrations()}}


@app.get("/v1/stack")
async def stack() -> dict[str, object]:
    started = time.perf_counter()
    integrations = await _live_integrations()
    payload = build_stack(
        integrations=integrations,
        replit=replit_platform.status(),
        api_keys_ready=apikeys.configured(),
        model=MODEL,
        agent_engine={"resource": agent_engine_resource(), "last_runtime": _LAST_AGENT_RUNTIME["runtime"]},
        model_armor={"template": model_armor.template_name(), "last_status": _LAST_AGENT_RUNTIME["model_armor"]},
        evidence_store=evidence.configured(),
        agent_quality=run_benchmark(ROOT).get("agent_quality"),
    )
    if _backend_url():
        # The Google group is the backend's own live view; only the Replit and app
        # groups are this host's to report.
        try:
            remote = (await asyncio.to_thread(_fetch_backend_json, "/v1/stack"))["data"]
            google = [dict(component, evidence=((component.get("evidence") or "") + " (reported by the Cloud Run backend)").strip()) for component in remote["components"] if component["group"] == "google"]
            payload["components"] = google + [component for component in payload["components"] if component["group"] != "google"]
            payload["backend"] = {"url": _backend_url(), "surface": remote.get("surface")}
        except Exception as exc:  # noqa: BLE001 - shown as unreachable rather than invented
            for component in payload["components"]:
                if component["group"] == "google":
                    component["status"] = "unreachable"
                    component["evidence"] = f"backend unreachable ({type(exc).__name__})"
        payload["summary"] = {
            state: sum(1 for c in payload["components"] if c["status"] == state)
            for state in ("live", "active", "configured", "applied", "pending", "unreachable")
        }
    payload["timing"] = {"query_ms": round((time.perf_counter() - started) * 1000, 1)}
    return {"data": payload, "disclaimer": validate_rendered_text(DISCLAIMER)}


# ------------------------------------------------------------------- keys ----


@app.post("/v1/keys")
async def create_api_key(request: Request) -> dict[str, object]:
    """Mint an API key with no account. Anonymous use keeps working without one."""
    _limited(request, "keys")
    if not apikeys.configured():
        raise _fail(
            503,
            "api_keys_unavailable",
            "This deployment has no signing secret configured, so it cannot issue keys.",
            "Every endpoint still works anonymously. Set DUTY_OF_CARE_API_KEY_SECRET to enable keys.",
        )
    return {"ok": True, "data": apikeys.mint(), "meta": {"request_id": _request_id()}}


@app.get("/v1/keys/self")
async def describe_api_key(request: Request) -> dict[str, object]:
    identity = _identity(request)
    return {
        "ok": True,
        "data": {
            "tier": identity.tier,
            "key_id": identity.key_id,
            "quota_multiplier": apikeys.TIER_MULTIPLIER[identity.tier],
            "limits_per_minute": {
                route: base * apikeys.TIER_MULTIPLIER[identity.tier] for route, base in BASE_LIMITS.items()
            },
            "keys_available": apikeys.configured(),
        },
    }


# ---------------------------------------------------------------- presets ----


@app.get("/v1/presets")
def presets() -> dict[str, object]:
    return {
        "data": {"presets": [item.summary() for item in all_presets()], "count": len(all_presets())},
        "disclaimer": validate_rendered_text(DISCLAIMER),
    }


@app.get("/v1/presets/{preset_id}")
def preset(preset_id: str) -> dict[str, object]:
    item = get_preset(preset_id)
    if item is None:
        raise _fail(404, "preset_not_found", f"No preset named {preset_id!r}.", "GET /v1/presets lists the ids.")
    return {"data": item.full(), "disclaimer": validate_rendered_text(DISCLAIMER)}


@app.get("/v1/presets/{preset_id}/download")
def preset_download(preset_id: str, format: str = "fountain") -> Response:
    item = get_preset(preset_id)
    if item is None:
        raise _fail(404, "preset_not_found", f"No preset named {preset_id!r}.", "GET /v1/presets lists the ids.")
    if format not in DOWNLOAD_FORMATS:
        raise _fail(400, "unsupported_format", f"format must be one of {', '.join(DOWNLOAD_FORMATS)}.", "Use ?format=fountain, txt, or json.")
    content, media_type, filename = download_payload(item, format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/v1/samples")
def samples() -> dict[str, object]:
    flagged = get_preset("guidance-case")
    clear = get_preset("responsible-depiction")
    return {
        "data": {
            "flagged": flagged.text if flagged else "",
            "not_flagged": clear.text if clear else "",
            "provenance": "self-authored CC0 demonstration scenes",
            "presets": "/v1/presets",
        },
        "disclaimer": validate_rendered_text(DISCLAIMER),
    }


# --------------------------------------------------------- corpus and help ----


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
            "corpus_version": _corpus_version(),
        },
        "disclaimer": validate_rendered_text(DISCLAIMER),
    }


@app.get("/v1/evidence")
def evidence_base() -> dict[str, object]:
    """The research behind the guidance: verified citations, findings, and trigger-class mapping."""
    loaded = evidence.local_records()
    return {
        "data": {
            "records": loaded["records"],
            "count": len(loaded["records"]),
            "verified_on": loaded["verified_on"],
            "verified_against": loaded["verified_against"],
            "evidence_version": replit_platform.corpus_version(evidence.EVIDENCE_PATH),
            "retrieval": "google_agent_search" if evidence.configured() else "not_configured_on_this_host",
        },
        "disclaimer": validate_rendered_text(DISCLAIMER),
    }


@app.get("/v1/eval/latest")
def eval_latest() -> dict[str, object]:
    """The deterministic-layer benchmark, computed live from the shipped cases."""
    return {"data": run_benchmark(ROOT), "disclaimer": validate_rendered_text(DISCLAIMER)}


# ----------------------------------------------------------------- review ----


class ReviewBody(ReviewRequest):
    screenplay: str = Field(default="", max_length=250_000)
    preset_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _resolve(self) -> ReviewBody:
        if not self.screenplay.strip():
            item = get_preset(self.preset_id or "")
            if item is None:
                raise ValueError("send a non-empty screenplay or a known preset_id")
            self.screenplay = item.text
        return self


Progress = Callable[[dict[str, Any]], Awaitable[None]]


async def _noop(_event: dict[str, Any]) -> None:
    return None


def _jurisdiction_summary(clauses: list[dict[str, Any]]) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    """Group clauses by jurisdiction and name the trigger classes several jurisdictions address.

    Multi-jurisdiction guidance is shown side by side, never merged into one voice.
    """
    by_jurisdiction: dict[str, list[str]] = {}
    coverage: dict[str, set[str]] = {}
    for clause in clauses:
        by_jurisdiction.setdefault(str(clause["jurisdiction"]), []).append(str(clause["clause_id"]))
        for klass in clause.get("trigger_classes", []):
            coverage.setdefault(str(klass), set()).add(str(clause["jurisdiction"]))
    divergence = [
        {"trigger_class": klass, "jurisdictions": sorted(regions)}
        for klass, regions in sorted(coverage.items())
        if len(regions) > 1
    ]
    return by_jurisdiction, divergence


async def _review(
    body: ReviewBody,
    identity: apikeys.ApiKeyIdentity,
    request_id: str,
    progress: Progress = _noop,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    scenes = {scene.scene_id: scene for scene in parse_scenes(body.screenplay)}
    scenes_for_grounding = dict(scenes)
    scenes_for_grounding[DOCUMENT_SCENE_ID] = document_scene(body.screenplay)
    triggers = detect_triggers(body.screenplay)
    await progress({"event": "parsed", "scenes": len(scenes), "candidates": len(triggers), "trigger_classes": sorted({t.trigger_class for t in triggers})})
    grounded_flags: list[dict[str, object]] = []
    configured = bool(os.getenv("VERTEX_SEARCH_DATA_STORE"))
    agent_ok, filter_ok, armor_ok = True, True, True
    if configured:
        scene_ids = sorted({item.scene_id for item in triggers if item.scene_id in scenes_for_grounding})[:10]

        async def ground_and_explain(scene_id: str) -> dict[str, object] | None:
            relevant = [item for item in triggers if item.scene_id == scene_id]
            scene = scenes_for_grounding[scene_id]
            await progress({"event": "retrieving", "scene_id": scene_id, "heading": scene.heading, "trigger_classes": sorted({t.trigger_class for t in relevant})})
            try:
                clauses = await asyncio.to_thread(retrieve_clauses, scene, relevant, body.region)
            except GroundingNotConfigured as exc:
                raise _fail(503, "grounding_not_configured", str(exc), "Configure VERTEX_SEARCH_DATA_STORE on the backend.") from exc
            except Exception as exc:
                raise _fail(
                    502,
                    "grounding_failed",
                    f"Agent Search failed closed ({type(exc).__name__}); no guidance flag was fabricated.",
                    "Retry shortly. The deterministic candidates are still available in a no-grounding run.",
                ) from exc
            await progress({"event": "retrieved", "scene_id": scene_id, "clause_count": len(clauses), "publishers": sorted({c.publisher for c in clauses})})
            if not clauses:
                return None
            # Research behind the guidance, from the second Agent Search store. Supplementary:
            # a retrieval failure here leaves the note intact rather than failing the review.
            try:
                research = await asyncio.to_thread(evidence.evidence_for, [item.trigger_class for item in relevant])
            except Exception:  # noqa: BLE001 - recorded as empty; the clauses are the decision, not this
                research = []
            await progress({"event": "explaining", "scene_id": scene_id, "runtime": "vertex_ai_agent_engine" if agent_engine_resource() else "adk_in_process", "evidence": len(research)})
            try:
                explanation = await explain_grounded_flag(
                    scene,
                    relevant,
                    clauses,
                    operator_id=identity.label,
                    document_level=scene_id == DOCUMENT_SCENE_ID,
                )
            except Exception as exc:
                raise _fail(
                    502,
                    "agent_review_failed",
                    f"The ADK review failed closed ({type(exc).__name__}); no explanation was fabricated.",
                    "Retry shortly. Retrieved clauses are never replaced by model memory.",
                ) from exc
            armor: dict[str, Any]
            if model_armor.configured():
                try:
                    armor = await asyncio.to_thread(model_armor.screen_model_response, str(explanation.get("text", "")))
                except Exception as exc:  # noqa: BLE001 - fail closed: withhold rather than guess
                    armor = {"status": "error", "template": model_armor.template_name(), "match": None, "detail": type(exc).__name__}
                if armor.get("match") or armor.get("status") == "error":
                    explanation["text"] = model_armor.WITHHELD
            else:
                armor = {"status": "not_configured", "template": None, "match": None}
            explanation["model_armor"] = armor
            _LAST_AGENT_RUNTIME.update(runtime=str(explanation.get("runtime")), model_armor=str(armor.get("status")))
            clause_dicts = [item.model_dump() for item in clauses]
            by_jurisdiction, divergence = _jurisdiction_summary(clause_dicts)
            await progress({"event": "explained", "scene_id": scene_id, "runtime": explanation.get("runtime"), "safety_filter": explanation.get("safety_filter"), "self_check_calls": explanation.get("self_check_calls"), "model_armor": armor.get("status")})
            return {
                "flag_id": "flag_" + sha256(f"{scene_id}:{','.join(item.clause_id for item in clauses)}".encode()).hexdigest()[:16],
                "scene_id": scene_id,
                "heading": scene.heading,
                "document_level": scene_id == DOCUMENT_SCENE_ID,
                "triggers": [item.model_dump() for item in relevant],
                "clauses": clause_dicts,
                "jurisdictions": by_jurisdiction,
                "divergence": divergence,
                "evidence": research,
                "agent": explanation,
                "state": "open",
            }

        # Scenes are independent, so retrieval and explanation run concurrently;
        # the first failure still fails the whole review closed.
        results = await asyncio.gather(*(ground_and_explain(scene_id) for scene_id in scene_ids))
        for flag in results:
            if flag is None:
                continue
            agent_ok = agent_ok and flag["agent"].get("status") == "completed"  # type: ignore[union-attr]
            filter_ok = filter_ok and flag["agent"].get("safety_filter") == "passed"  # type: ignore[union-attr]
            armor = flag["agent"].get("model_armor", {})  # type: ignore[union-attr]
            armor_ok = armor_ok and armor.get("status") == "screened" and not armor.get("match")
            grounded_flags.append(flag)
    trigger_classes = sorted({item.trigger_class for item in triggers})
    thresholds = {
        "deterministic_candidate_present": bool(triggers),
        "applicable_clause_retrieved": bool(grounded_flags),
        "agent_explanation_completed": bool(grounded_flags) and agent_ok,
        "safety_filter_passed": (not grounded_flags) or filter_ok,
        "model_armor_clear": bool(grounded_flags) and model_armor.configured() and armor_ok,
        "resource_signpost_present": "signposting_absence" not in trigger_classes,
        "grounding_available": configured,
    }
    if not model_armor.configured():
        thresholds.pop("model_armor_clear")
    runtimes = sorted({str(flag["agent"].get("runtime")) for flag in grounded_flags})  # type: ignore[union-attr]
    data = {
        "scenes": [scene.model_dump() for scene in scenes.values()],
        "grounded_flags": grounded_flags,
        "trigger_candidates": [item.model_dump() for item in triggers],
        "grounding_status": "available" if configured else "not_configured",
        "writer_controls": ["accept", "dismiss", "request_expert_review"],
        "resources": resources_for(body.region),
        "disclaimer": validate_rendered_text(DISCLAIMER),
        "decision_owner": "writer",
        "overall_score": None,
    }
    latency_ms = round((time.perf_counter() - started) * 1000)
    meta = {
        "request_id": request_id,
        "latency_ms": latency_ms,
        "caller": {"tier": identity.tier, "key_id": identity.key_id},
        "verdict": "notes" if grounded_flags else ("candidates" if triggers else "no_candidates"),
        "gate": {
            "passed": [name for name, ok in thresholds.items() if ok],
            "failed": [name for name, ok in thresholds.items() if not ok],
        },
        "counts": {"scenes": len(scenes), "candidates": len(triggers), "notes": len(grounded_flags)},
        "model_versions": {"gemini": MODEL, "google_adk": _version("google-adk")},
        "agent_runtime": runtimes,
        "model_armor": model_armor.template_name().rsplit("/", 1)[-1] if model_armor.template_name() else None,
        "region": body.region.upper(),
        "region_known": body.region.upper() in REGIONS,
        "corpus_version": _corpus_version(),
        "surface": replit_platform.runtime()["surface"],
        "abstained_because": None if configured else "grounding is not configured on this host, so no note can be raised",
    }
    telemetry.emit(
        "review",
        request_id=request_id,
        caller_tier=identity.tier,
        key_id=identity.key_id,
        region=body.region,
        scenes=len(scenes),
        trigger_classes=trigger_classes,
        notes=len(grounded_flags),
        clauses=sum(len(flag["clauses"]) for flag in grounded_flags),  # type: ignore[arg-type]
        model=MODEL,
        latency_ms=latency_ms,
        surface=meta["surface"],
        agent_runtime=runtimes,
    )
    await progress({"event": "complete", "notes": len(grounded_flags), "latency_ms": latency_ms})
    return data, meta


@app.post("/v1/review")
async def review(body: ReviewBody, request: Request, format: Literal["json", "markdown"] = "json") -> Response:
    """Review a screenplay. Returns notes with cited clauses; never a score."""
    identity = _limited(request, "review")
    request_id = _request_id()
    data, meta = await _review(body, identity, request_id)
    if format == "markdown":
        title = get_preset(body.preset_id).title if body.preset_id and get_preset(body.preset_id) else None
        return Response(
            content=render_markdown(data, meta, title=title),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="duty-of-care-{request_id}.md"'},
        )
    return JSONResponse({"ok": True, "data": data, "meta": meta})


@app.post("/v1/review/stream")
async def review_stream(body: ReviewBody, request: Request) -> StreamingResponse:
    """The same review as newline-delimited JSON progress events, ending with the full result.

    Each line is one JSON object: parsed, retrieving, retrieved, explaining,
    explained, complete, then result (with data and meta) or error (with the
    error envelope). Nothing is computed differently from POST /v1/review.
    """
    identity = _limited(request, "review")
    request_id = _request_id()
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def push(event: dict[str, Any]) -> None:
        await queue.put({**event, "request_id": request_id})

    async def run() -> None:
        try:
            data, meta = await _review(body, identity, request_id, progress=push)
            await queue.put({"event": "result", "ok": True, "data": data, "meta": meta})
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {"code": "request_error", "message": str(exc.detail)}
            await queue.put({"event": "error", "ok": False, "status": exc.status_code, "error": {**detail, "docs": "/docs"}, "meta": {"request_id": request_id}})
        except Exception as exc:  # noqa: BLE001 - the stream must end with a typed error, never hang
            await queue.put({"event": "error", "ok": False, "status": 500, "error": {"code": "internal_error", "message": type(exc).__name__, "fix": "Retry; nothing was fabricated.", "docs": "/docs"}, "meta": {"request_id": request_id}})
        finally:
            await queue.put(None)

    task = asyncio.create_task(run())

    async def lines():
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield json.dumps(item, default=str) + "\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(lines(), media_type="application/x-ndjson", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# --------------------------------------------- Replit identity and storage ----


def _writer(request: Request) -> replit_platform.WriterIdentity:
    identity = replit_platform.identity_from_headers(request.headers)
    if identity is None:
        raise _fail(
            401,
            "sign_in_required",
            "Saving decisions needs a signed-in writer.",
            "Sign in with Replit Auth on the Replit surface. Anonymous review never needs this.",
        )
    return identity


@app.get("/v1/me")
async def me(request: Request) -> dict[str, object]:
    identity = replit_platform.identity_from_headers(request.headers)
    return {
        "ok": True,
        "data": {
            "signed_in": identity is not None,
            "identity": identity.to_dict() if identity else None,
            "runtime": replit_platform.runtime(),
        },
    }


class DecisionBody(BaseModel):
    flag_id: str = Field(max_length=64)
    scene_id: str = Field(max_length=32)
    heading: str = Field(max_length=200)
    decision: Literal["accepted", "dismissed", "expert_review"]
    reason: str = Field(default="", max_length=2000)
    clause_ids: list[str] = Field(default_factory=list, max_length=20)
    scene_text: str = Field(default="", max_length=250_000)


@app.get("/v1/decisions")
async def list_decisions(request: Request) -> dict[str, object]:
    writer = _writer(request)
    store = replit_platform.decision_store()
    records = store.list(writer.user_id)
    version = _corpus_version()
    return {
        "ok": True,
        "data": {
            "decisions": records,
            "backend": store.backend,
            "corpus_version": version,
            "stale": [item["decision_id"] for item in records if item.get("corpus_version") != version],
            "last_recheck": store.get_system(replit_platform.RECHECK_KEY),
        },
        "disclaimer": validate_rendered_text(DISCLAIMER),
    }


@app.post("/v1/decisions")
async def save_decision(body: DecisionBody, request: Request) -> dict[str, object]:
    _limited(request, "decisions")
    writer = _writer(request)
    store = replit_platform.decision_store()
    record = {
        "decision_id": "dec_" + secrets.token_hex(6),
        "flag_id": body.flag_id,
        "scene_id": body.scene_id,
        "heading": body.heading,
        "decision": body.decision,
        "reason": body.reason,
        "clause_ids": body.clause_ids,
        "scene_fingerprint": sha256(body.scene_text.encode("utf-8")).hexdigest()[:16] if body.scene_text else None,
        "corpus_version": _corpus_version(),
        "created_at": replit_platform.now_iso(),
    }
    store.put(writer.user_id, record)
    return {"ok": True, "data": {"decision": record, "backend": store.backend, "stored_screenplay_text": False}}


@app.delete("/v1/decisions/{decision_id}")
async def delete_decision(decision_id: str, request: Request) -> dict[str, object]:
    writer = _writer(request)
    removed = replit_platform.decision_store().delete(writer.user_id, decision_id)
    if not removed:
        raise _fail(404, "decision_not_found", "No such decision for this writer.", "GET /v1/decisions lists yours.")
    return {"ok": True, "data": {"deleted": decision_id}}


class ExportBody(BaseModel):
    title: str = Field(default="submitted screenplay", max_length=200)
    review: dict[str, Any]
    meta: dict[str, Any] = Field(default_factory=dict)


@app.post("/v1/exports")
async def create_export(body: ExportBody, request: Request) -> dict[str, object]:
    """Store a review result only because the writer asked for it."""
    _limited(request, "exports")
    if "disclaimer" not in body.review:
        raise _fail(422, "disclaimer_required", "An export must carry data.disclaimer.", "Send the review payload exactly as /v1/review returned it.")
    payload = json.dumps(
        {"title": body.title, "exported_at": replit_platform.now_iso(), "review": body.review, "meta": body.meta},
        indent=2,
    )
    export_id, backend, note = replit_platform.put_export(body.title, payload)
    return {
        "ok": True,
        "data": {"export_id": export_id, "url": f"/v1/exports/{export_id}", "backend": backend, "note": note, "bytes": len(payload)},
    }


@app.get("/v1/exports/{export_id}")
async def get_export(export_id: str) -> Response:
    text = replit_platform.get_export(export_id)
    if text is None:
        raise _fail(404, "export_not_found", "No export with that id on this host.", "Exports on Cloud Run are ephemeral; on Replit they live in App Storage.")
    return Response(
        content=text,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{export_id}.json"'},
    )


class ReportBody(BaseModel):
    title: str = Field(default="submitted screenplay", max_length=200)
    review: dict[str, Any]
    meta: dict[str, Any] = Field(default_factory=dict)


@app.post("/v1/report")
async def report(body: ReportBody) -> Response:
    """Render a Markdown report from a review payload. No model call, nothing stored."""
    if "disclaimer" not in body.review:
        raise _fail(422, "disclaimer_required", "A report must carry data.disclaimer.", "Send the review payload exactly as /v1/review returned it.")
    request_id = str(body.meta.get("request_id") or _request_id())
    return Response(
        content=render_markdown(body.review, body.meta, title=body.title),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="duty-of-care-{request_id}.md"'},
    )


app.mount("/static", StaticFiles(directory=WEB), name="static")
