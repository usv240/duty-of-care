"""Google Cloud Model Armor screening of the agent's final answer.

The project's own filter is a regular expression that knows exactly two
things: certification language and method specificity. Model Armor is Google's
managed screen for the categories that filter cannot see: hate speech,
harassment, sexually explicit content, dangerous content, prompt-injection
patterns, malicious URIs, and sensitive data. It runs on the text the writer
will read, after the ADK agent has finished and after the project filter has
passed, and it can only withhold, never author.

The template lives in the same project and region as the model. When the
template is not configured the screen reports `not_configured`, so the stack
panel never claims a screen that did not run.
"""

from __future__ import annotations

import os
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession

TEMPLATE_ENV = "MODEL_ARMOR_TEMPLATE"
WITHHELD = (
    "The generated text was withheld because Google Cloud Model Armor reported a match "
    "in a category the writer should not receive. The retrieved clauses remain available "
    "for human review."
)


def template_name() -> str | None:
    value = os.getenv(TEMPLATE_ENV)
    return value if value else None


def configured() -> bool:
    return template_name() is not None


def _endpoint(template: str) -> str:
    # projects/{p}/locations/{l}/templates/{t}
    location = template.split("/locations/")[1].split("/")[0]
    return f"https://modelarmor.{location}.rep.googleapis.com/v1/{template}:sanitizeModelResponse"


def _project_id(template: str) -> str:
    return template.split("/projects/")[-1].split("/")[0] if "/projects/" in template else template.split("projects/")[1].split("/")[0]


def screen_model_response(text: str, *, timeout: int = 20) -> dict[str, Any]:
    """Screen agent output. Returns a record the API embeds in the flag."""
    template = template_name()
    if template is None:
        return {"status": "not_configured", "template": None, "match": None}
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session = AuthorizedSession(credentials)
    response = session.post(
        _endpoint(template),
        json={"modelResponseData": {"text": text}},
        headers={"X-Goog-User-Project": _project_id(template)},
        timeout=timeout,
    )
    if not response.ok:
        raise RuntimeError(f"Model Armor HTTP {response.status_code}: {response.text[:200]}")
    result = response.json().get("sanitizationResult", {})
    state = str(result.get("filterMatchState", "UNKNOWN"))
    filters = result.get("filterResults", {})
    matched = sorted(
        name
        for name, value in filters.items()
        if _match_state(value) == "MATCH_FOUND"
    )
    return {
        "status": "screened",
        "template": template.rsplit("/", 1)[-1],
        "match": state == "MATCH_FOUND",
        "matched_filters": matched,
        "invocation_id": result.get("invocationResult"),
    }


def _match_state(value: Any) -> str | None:
    """Filter results nest their match state one or two levels down."""
    if not isinstance(value, dict):
        return None
    for key, inner in value.items():
        if key == "matchState":
            return str(inner)
        if isinstance(inner, dict):
            found = _match_state(inner)
            if found:
                return found
    return None
