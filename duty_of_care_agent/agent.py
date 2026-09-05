"""GuidanceContextReviewer: a Google ADK agent bound to one scene through session state.

Everything the agent may know about a review arrives in the session state that
the backend sets when it creates the session: the scene, the deterministic
triggers, and the clauses Google Agent Search retrieved. The agent reaches that
state only through `get_bound_guidance`, and it must pass its draft alternative
through `check_alternative`, which runs the same hard filter the API applies
again afterwards. The agent decides nothing: code decided that a flag exists,
and the writer decides what to do with it.

This module has no web dependencies so it can be shipped to Vertex AI Agent
Engine as an extra package alongside `duty_of_care.filters`.
"""

from __future__ import annotations

import os
import re
from typing import Any

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools import ToolContext
from google.genai import types

from duty_of_care.filters import specificity_score, validate_rendered_text, validate_suggestion

AGENT_NAME = "GuidanceContextReviewer"
ALTERNATIVE_HEADING = "One alternative that keeps the drama"
WITHHELD = (
    "The generated alternative was withheld because a hard safety-language filter rejected "
    "it. The retrieved clauses remain available for human review."
)
BLOCKED = (
    "The model returned no text because Gemini's safety settings blocked the response. "
    "The retrieved clauses remain available for human review."
)
_ALTERNATIVE_SPLIT = re.compile(re.escape(ALTERNATIVE_HEADING), re.IGNORECASE)

SCENE_INSTRUCTION = (
    "You support a screenwriter; you are not a censor or clinician. Work in this order. "
    "1) Call get_bound_guidance exactly once. 2) Draft one concise alternative for the scene "
    "that preserves its dramatic intent, then call check_alternative with that draft; if it "
    "is rejected, revise and check again until accepted. 3) Write your final answer for the "
    "writer with exactly these three parts, in plain language: a section titled 'Why this "
    "guidance may apply' with one short paragraph per retrieved clause naming the publisher "
    "and how the clause relates to what happens in this scene, without quoting or "
    "paraphrasing any method, quantity, or procurement detail from the scene; a section "
    f"titled '{ALTERNATIVE_HEADING}' containing only the accepted draft; and one closing "
    "sentence stating that the writer may accept, dismiss, or ask for expert review. Do not "
    "mention tools, checks, or that anything was accepted. Never add procedural, "
    "procurement, location, quantity, dosage, or method detail. Never say a scene is safe, "
    "harmful, approved, compliant, or certified. Do not issue a score or verdict. Do not "
    "repeat crisis-method details from the source scene."
)

DOCUMENT_INSTRUCTION = (
    "You support a screenwriter; you are not a censor or clinician. This note concerns the "
    "whole document, not one scene: no support-resource signpost was found anywhere in it. "
    "Work in this order. 1) Call get_bound_guidance exactly once. 2) Draft one concise "
    "suggestion for where and how a resource signpost could sit in this document (for "
    "example an end card, a title card, or a line of dialogue that names a real support "
    "route) without rewriting or quoting any scene, then call check_alternative with that "
    "draft; if it is rejected, revise and check again until accepted. 3) Write your final "
    "answer with exactly these three parts, in plain language: a section titled 'Why this "
    "guidance may apply' with one short paragraph per retrieved clause naming the publisher; "
    f"a section titled '{ALTERNATIVE_HEADING}' containing only the accepted suggestion; and "
    "one closing sentence stating that the writer may accept, dismiss, or ask for expert "
    "review. Do not mention tools or checks. Never quote scene text. Never add procedural, "
    "procurement, location, quantity, dosage, or method detail. Never say the document is "
    "safe, harmful, approved, compliant, or certified. Do not issue a score or verdict."
)

INSTRUCTION = (
    "The session state tells you whether this is a scene-level or a document-level review. "
    "If the state says document_level is true, follow these rules:\n" + DOCUMENT_INSTRUCTION +
    "\nOtherwise follow these rules:\n" + SCENE_INSTRUCTION
)

# Explicit Gemini safety settings. Dangerous-content is set to block only at high
# confidence because the scenes under review legitimately discuss suicide and
# self-harm; the project's own filters and Model Armor cover what remains.
SAFETY_SETTINGS = [
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
]
SAFETY_SETTINGS_SUMMARY = {
    str(item.category).rsplit("_", 1)[-1].lower() if "HARM_CATEGORY_" not in str(item.category) else str(item.category).replace("HarmCategory.", "").replace("HARM_CATEGORY_", "").lower(): str(item.threshold).replace("HarmBlockThreshold.", "")
    for item in SAFETY_SETTINGS
}


async def get_bound_guidance(tool_context: ToolContext) -> dict[str, Any]:
    """Return the source-linked clauses and deterministic triggers bound to this review.

    Call this exactly once before writing anything. It is the only source of
    guidance text you may use.
    """

    state = tool_context.state
    return {
        "scene_id": state.get("scene_id"),
        "document_level": bool(state.get("document_level")),
        "clauses": list(state.get("clauses", [])),
        "deterministic_triggers": list(state.get("triggers", [])),
    }


async def check_alternative(alternative: str, tool_context: ToolContext) -> dict[str, Any]:
    """Run the hard safety filter on a draft alternative before you present it.

    Returns accepted=false with a reason when the draft adds method specificity
    or uses certification language. Revise and call again if rejected.
    """

    scene_text = str(tool_context.state.get("scene_text", ""))
    try:
        validate_rendered_text(alternative)
        validate_suggestion(scene_text, alternative)
    except ValueError as exc:
        return {
            "accepted": False,
            "reason": str(exc),
            "specificity_original": specificity_score(scene_text),
            "specificity_draft": specificity_score(alternative),
        }
    return {"accepted": True, "reason": "passes the hard filter"}


def build_agent(model: str | None = None) -> LlmAgent:
    return LlmAgent(
        name=AGENT_NAME,
        model=model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        description="Explains retrieved screen-guidance clauses for one scene and drafts one filtered alternative.",
        instruction=INSTRUCTION,
        tools=[get_bound_guidance, check_alternative],
        generate_content_config=types.GenerateContentConfig(safety_settings=SAFETY_SETTINGS),
    )


root_agent = build_agent()


def _normalise(text: str) -> str:
    return " ".join(text.replace("*", "").replace("_", "").split()).strip().lower()


def apply_output_filter(
    scene_text: str, text: str, accepted_drafts: list[str] | None = None
) -> tuple[str, str]:
    """Enforce the hard filter on the agent's final answer.

    Certification language is rejected anywhere in the text. The specificity
    comparison applies to the alternative section, because the explanation may
    legitimately name a clause about method detail without adding any. If the
    alternative section is, verbatim, a draft the check_alternative tool already
    accepted for this scene, that acceptance stands; anything else is compared
    by the same rule again. If the answer has no alternative section, the whole
    text is compared.
    """
    if not text.strip():
        return BLOCKED, "blocked"
    try:
        validate_rendered_text(text)
        parts = _ALTERNATIVE_SPLIT.split(text, maxsplit=1)
        alternative = parts[1] if len(parts) == 2 else text
        remainder = _normalise(alternative)
        for draft in accepted_drafts or []:
            accepted = _normalise(draft)
            if accepted and accepted in remainder:
                # Text the tool accepted for this scene stands; only what surrounds it is re-checked.
                remainder = remainder.replace(accepted, " ")
        validate_suggestion(scene_text, remainder)
    except ValueError:
        return WITHHELD, "rejected"
    return text, "passed"


def review_prompt(state: dict[str, Any]) -> str:
    if state.get("document_level"):
        classes = ", ".join(sorted({str(t.get("trigger_class")) for t in state.get("triggers", [])}))
        return (
            "Document-level review. The document has no support-resource signpost. "
            f"Trigger classes: {classes}. Document excerpt for context only, never to be "
            f"quoted: {str(state.get('scene_text', ''))[:3000]}"
        )
    return (
        f"Review {state.get('scene_id')}. Heading: {state.get('scene_heading')}. "
        f"Scene text: {str(state.get('scene_text', ''))[:6000]}"
    )
