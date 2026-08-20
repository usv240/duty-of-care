from __future__ import annotations

import json
import os
import uuid
from typing import Any

from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .filters import validate_rendered_text, validate_suggestion
from .models import GuidanceClause, Scene, Trigger


MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
APP_NAME = "duty_of_care"


async def explain_grounded_flag(
    scene: Scene,
    triggers: list[Trigger],
    clauses: list[GuidanceClause],
    *,
    operator_id: str,
) -> dict[str, Any]:
    """Use ADK/Gemini to explain retrieved evidence; code already made the flag decision."""

    async def get_bound_guidance() -> dict[str, object]:
        """Return source-linked clauses bound to this reviewed scene."""

        return {
            "scene_id": scene.scene_id,
            "clauses": [item.model_dump() for item in clauses],
            "deterministic_triggers": [item.model_dump() for item in triggers],
        }

    agent = LlmAgent(
        name="GuidanceContextReviewer",
        model=MODEL,
        instruction=(
            "You support a screenwriter; you are not a censor or clinician. You MUST call "
            "get_bound_guidance exactly once. Explain why the retrieved guidance may apply in "
            "this narrative context and offer one concise alternative that preserves dramatic "
            "intent. Never add procedural, procurement, location, quantity, dosage, or method "
            "detail. Never say a scene is safe, harmful, approved, compliant, or certified. "
            "Do not issue a score or verdict. State that the writer may accept, dismiss, or ask "
            "for expert review. Do not repeat crisis-method details from the source scene."
        ),
        tools=[get_bound_guidance],
    )
    service = InMemorySessionService()
    session_id = f"care_{uuid.uuid4().hex[:12]}"
    await service.create_session(app_name=APP_NAME, user_id=operator_id, session_id=session_id)
    runner = Runner(app_name=APP_NAME, agent=agent, session_service=service)
    message = types.Content(
        role="user",
        parts=[
            types.Part(
                text=(
                    f"Review {scene.scene_id}. Heading: {scene.heading}. "
                    f"Scene text: {scene.text[:6000]}"
                )
            )
        ],
    )
    transcript: list[dict[str, str]] = []
    async for event in runner.run_async(
        user_id=operator_id, session_id=session_id, new_message=message
    ):
        parts = getattr(getattr(event, "content", None), "parts", None) or []
        text_parts = [part.text for part in parts if getattr(part, "text", None)]
        if text_parts:
            transcript.append(
                {"author": str(getattr(event, "author", "agent")), "text": "\n".join(text_parts)}
            )
    text = transcript[-1]["text"] if transcript else ""
    try:
        validate_rendered_text(text)
        validate_suggestion(scene.text, text)
        filter_status = "passed"
    except ValueError:
        text = "The generated alternative was withheld because a hard safety-language filter rejected it. The retrieved clauses remain available for human review."
        filter_status = "rejected"
    return {
        "status": "completed",
        "session_id": session_id,
        "agent": "GuidanceContextReviewer",
        "model": MODEL,
        "decision_source": "deterministic_trigger_plus_agent_search_clause",
        "guidance_transport": "google_agent_search",
        "safety_filter": filter_status,
        "text": validate_rendered_text(text),
        "requires_human": True,
        "tool_contract": json.dumps({"bound_scene": scene.scene_id, "clause_count": len(clauses)}),
    }
