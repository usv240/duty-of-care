"""Layer two, second half: the GuidanceContextReviewer explains what retrieval returned.

Code has already decided that a flag exists (a deterministic trigger plus an
applicable retrieved clause). The agent is bound to that one scene and those
clauses through session state and a tool, and it must run the same hard safety
filter the API applies afterwards through a second tool before it answers.

Two runtimes execute the identical agent definition from `duty_of_care_agent`:

* Vertex AI Agent Engine, the managed runtime, when AGENT_ENGINE_RESOURCE is set.
* Google ADK in-process on this host, which is also the fallback if the managed
  runtime fails, recorded as such in the response so nothing is silently hidden.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from duty_of_care_agent.agent import (
    AGENT_NAME,
    ALTERNATIVE_HEADING,
    SAFETY_SETTINGS_SUMMARY,
    WITHHELD,
    apply_output_filter,
    build_agent,
    review_prompt,
)

from .models import GuidanceClause, Scene, Trigger

__all__ = ["ALTERNATIVE_HEADING", "WITHHELD", "apply_output_filter", "explain_grounded_flag"]

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
APP_NAME = "duty_of_care"
RESOURCE_ENV = "AGENT_ENGINE_RESOURCE"
_REMOTE: dict[str, Any] = {}


def agent_engine_resource() -> str | None:
    value = os.getenv(RESOURCE_ENV)
    return value if value else None


def _remote_engine() -> Any:
    """The managed agent handle, created once per process."""
    resource = agent_engine_resource()
    if resource is None:
        raise RuntimeError("AGENT_ENGINE_RESOURCE is not set")
    if _REMOTE.get("name") != resource:
        import vertexai
        from vertexai import agent_engines

        vertexai.init(
            project=os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
        _REMOTE.update(name=resource, engine=agent_engines.get(resource))
    return _REMOTE["engine"]


def _collect(event: Any, transcript: list[dict[str, str]], tool_calls: list[dict[str, Any]]) -> None:
    """Read text and tool activity off one event, whether an ADK object or a plain dict."""
    if isinstance(event, dict):
        content = event.get("content") or {}
        parts = content.get("parts") or []
        author = str(event.get("author", "agent"))
    else:
        parts = getattr(getattr(event, "content", None), "parts", None) or []
        author = str(getattr(event, "author", "agent"))
    texts: list[str] = []
    for part in parts:
        get = part.get if isinstance(part, dict) else lambda key, _p=part: getattr(_p, key, None)
        call = get("function_call")
        if call:
            name = call.get("name") if isinstance(call, dict) else getattr(call, "name", None)
            args = call.get("args") if isinstance(call, dict) else getattr(call, "args", None)
            if name:
                entry: dict[str, Any] = {"tool": str(name), "author": author}
                if name == "check_alternative" and isinstance(args, dict) and args.get("alternative"):
                    entry["draft"] = str(args["alternative"])
                tool_calls.append(entry)
        response = get("function_response")
        if response:
            name = response.get("name") if isinstance(response, dict) else getattr(response, "name", None)
            if name == "check_alternative":
                payload = response.get("response") if isinstance(response, dict) else getattr(response, "response", None)
                tool_calls.append(
                    {"tool": "check_alternative:result", "accepted": bool(dict(payload or {}).get("accepted"))}
                )
        text = get("text")
        if text:
            texts.append(str(text))
    if texts:
        transcript.append({"author": author, "text": "\n".join(texts)})


async def _run_local(state: dict[str, Any], prompt: str, operator_id: str) -> tuple[str, list[dict[str, str]], list[dict[str, Any]]]:
    agent = build_agent(MODEL)
    service = InMemorySessionService()
    session_id = f"care_{uuid.uuid4().hex[:12]}"
    await service.create_session(app_name=APP_NAME, user_id=operator_id, session_id=session_id, state=state)
    runner = Runner(app_name=APP_NAME, agent=agent, session_service=service)
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    transcript: list[dict[str, str]] = []
    tool_calls: list[dict[str, Any]] = []
    async for event in runner.run_async(user_id=operator_id, session_id=session_id, new_message=message):
        _collect(event, transcript, tool_calls)
    return session_id, transcript, tool_calls


def _run_remote_sync(state: dict[str, Any], prompt: str, operator_id: str) -> tuple[str, list[dict[str, str]], list[dict[str, Any]]]:
    engine = _remote_engine()
    session = engine.create_session(user_id=operator_id, state=state)
    session_id = str(session["id"] if isinstance(session, dict) else getattr(session, "id"))
    transcript: list[dict[str, str]] = []
    tool_calls: list[dict[str, Any]] = []
    for event in engine.stream_query(user_id=operator_id, session_id=session_id, message=prompt):
        _collect(event, transcript, tool_calls)
    return session_id, transcript, tool_calls


async def explain_grounded_flag(
    scene: Scene,
    triggers: list[Trigger],
    clauses: list[GuidanceClause],
    *,
    operator_id: str,
    document_level: bool = False,
) -> dict[str, Any]:
    """Run the agent; code already made the flag decision."""

    state = {
        "scene_id": scene.scene_id,
        "scene_heading": scene.heading,
        "scene_text": scene.text,
        "document_level": document_level,
        "clauses": [item.model_dump() for item in clauses],
        "triggers": [item.model_dump() for item in triggers],
    }
    prompt = review_prompt(state)
    runtime = "adk_in_process"
    runtime_note: str | None = None
    if agent_engine_resource():
        try:
            try:
                session_id, transcript, tool_calls = await asyncio.to_thread(_run_remote_sync, state, prompt, operator_id)
            except Exception as first:  # noqa: BLE001 - one retry absorbs a transient quota or cold-start error
                if type(first).__name__ not in {"ResourceExhausted", "ServiceUnavailable", "DeadlineExceeded"}:
                    raise
                await asyncio.sleep(4)
                session_id, transcript, tool_calls = await asyncio.to_thread(_run_remote_sync, state, prompt, operator_id)
            if not any(item["text"].strip() for item in transcript):
                raise RuntimeError("AgentEngineEmptyAnswer")
            runtime = "vertex_ai_agent_engine"
        except Exception as exc:  # noqa: BLE001 - recorded, then the in-process runtime takes over
            reason = str(exc) if type(exc).__name__ == "RuntimeError" else type(exc).__name__
            runtime_note = f"Agent Engine failed ({reason}); the identical agent ran in-process."
            session_id, transcript, tool_calls = await _run_local(state, prompt, operator_id)
            runtime = "adk_in_process_fallback"
    else:
        session_id, transcript, tool_calls = await _run_local(state, prompt, operator_id)

    # Drafts the tool accepted, in order: a check_alternative call followed by an accepted result.
    accepted_drafts: list[str] = []
    for index, item in enumerate(tool_calls):
        if item["tool"] == "check_alternative:result" and item.get("accepted"):
            for previous in reversed(tool_calls[:index]):
                if previous["tool"] == "check_alternative":
                    if previous.get("draft"):
                        accepted_drafts.append(str(previous["draft"]))
                    break
    text, filter_status = apply_output_filter(
        scene.text, transcript[-1]["text"] if transcript else "", accepted_drafts
    )
    return {
        "status": "completed",
        "session_id": session_id,
        "agent": AGENT_NAME,
        "model": MODEL,
        "runtime": runtime,
        "runtime_note": runtime_note,
        "decision_source": "deterministic_trigger_plus_agent_search_clause",
        "guidance_transport": "google_agent_search",
        "safety_filter": filter_status,
        "safety_settings": SAFETY_SETTINGS_SUMMARY,
        "self_check_calls": sum(1 for item in tool_calls if item["tool"] == "check_alternative"),
        "accepted_drafts": len(accepted_drafts),
        "tool_calls": [{key: value for key, value in item.items() if key != "draft"} for item in tool_calls],
        "document_level": document_level,
        "text": text,
        "requires_human": True,
        "tool_contract": json.dumps({"bound_scene": scene.scene_id, "clause_count": len(clauses)}),
    }
