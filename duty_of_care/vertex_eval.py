"""Vertex AI Gen AI Evaluation Service, used as an independent judge of the agent's answers.

The project's own filters decide what a writer may see. This module asks a
different Google service a different question afterwards: is the explanation
the agent wrote actually grounded in the clauses Agent Search retrieved, and is
it safe? Scores are published in docs/EVAL-GROUNDEDNESS.json and served from
/v1/eval/latest, so the number on the site is the number that ran.
"""

from __future__ import annotations

import os
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession


def _endpoint() -> str:
    project = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT", "agentic-fleet-2026")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    return (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}"
        ":evaluateInstances"
    )


def _session() -> AuthorizedSession:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return AuthorizedSession(credentials)


def _call(body: dict[str, Any]) -> dict[str, Any]:
    response = _session().post(_endpoint(), json=body, timeout=180)
    if not response.ok:
        raise RuntimeError(f"evaluation service HTTP {response.status_code}: {response.text[:300]}")
    return response.json()


def groundedness(prediction: str, context: str) -> dict[str, Any]:
    """Pointwise groundedness (0 to 1): is every claim in the answer supported by the context?"""
    result = _call(
        {"groundednessInput": {"metricSpec": {}, "instance": {"prediction": prediction, "context": context}}}
    )["groundednessResult"]
    return {
        "score": result.get("score"),
        "confidence": result.get("confidence"),
        "explanation": str(result.get("explanation", ""))[:1200],
    }


def safety(prediction: str) -> dict[str, Any]:
    """Pointwise safety (0 to 1) of the answer text on its own."""
    result = _call({"safetyInput": {"metricSpec": {}, "instance": {"prediction": prediction}}})["safetyResult"]
    return {
        "score": result.get("score"),
        "confidence": result.get("confidence"),
        "explanation": str(result.get("explanation", ""))[:800],
    }


def clause_context(
    clauses: list[dict[str, Any]],
    jurisdiction: str | None = None,
    *,
    scene_text: str = "",
    triggers: list[dict[str, Any]] | None = None,
) -> str:
    """The context the judge may hold the agent to: exactly the agent's own inputs.

    That is the retrieved clauses, the scene under review, and the deterministic
    triggers. Anything the explanation says beyond these is, by construction,
    ungrounded.
    """
    lines = []
    if scene_text:
        lines.append(f"Scene under review (the writer's own text): {scene_text[:6000]}")
    for trigger in triggers or []:
        lines.append(
            f"Deterministic trigger {trigger.get('trigger_class')}: {trigger.get('rule')} "
            f"Matched text: {trigger.get('matched_text') or 'n/a'}."
        )
    for clause in clauses:
        lines.append(
            f"{clause.get('publisher')} ({clause.get('jurisdiction')}, {clause.get('document_title')}, "
            f"version {clause.get('version')}): {clause.get('clause')}"
        )
    lines.append(
        "The writer may accept, dismiss, or ask for expert review. The agent may propose one "
        "alternative that keeps the dramatic intent and adds no method detail."
    )
    if jurisdiction:
        lines.append(f"Region requested: {jurisdiction}.")
    return "\n".join(lines)
