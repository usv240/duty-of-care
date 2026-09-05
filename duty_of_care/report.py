"""Downloadable views over a review result. Never a second source of truth.

The Markdown report is rendered from the same structured payload the API
returns, so a writer's export and an integrator's JSON cannot disagree. The
disclaimer and the crisis resources are rendered first because a report that is
printed and handed to someone must carry them even if the reader stops there.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

CLASS_LABEL = {
    "method_specificity": "Method specificity",
    "framing_as_solution": "Framed as a solution",
    "absence_of_help_seeking": "No help-seeking signal",
    "romanticisation": "Romanticisation",
    "repetition": "Repetition",
    "signposting_absence": "No resource signpost",
}


def _line(text: str) -> str:
    return " ".join(str(text).split())


def render_markdown(
    data: Mapping[str, Any],
    meta: Mapping[str, Any],
    *,
    title: str | None = None,
) -> str:
    lines: list[str] = []
    lines.append(f"# Duty of Care pre-review: {title or 'submitted screenplay'}")
    lines.append("")
    lines.append(f"> {_line(data.get('disclaimer', ''))}")
    lines.append(">")
    lines.append("> Decision owner: the writer. Overall score: deliberately absent.")
    lines.append("")
    lines.append("## Support resources")
    lines.append("")
    for resource in data.get("resources", []):
        lines.append(
            f"- **{resource.get('name')}**: {resource.get('contact')} ({resource.get('url')})"
        )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    scenes = data.get("scenes", [])
    flags = data.get("grounded_flags", [])
    candidates = data.get("trigger_candidates", [])
    lines.append(f"- Scenes parsed: {len(scenes)}")
    lines.append(f"- Deterministic candidates: {len(candidates)}")
    lines.append(f"- Grounded guidance notes: {len(flags)}")
    lines.append(f"- Grounding: {data.get('grounding_status')}")
    gate = meta.get("gate", {})
    if gate:
        lines.append(f"- Gate passed: {', '.join(gate.get('passed', [])) or 'none'}")
        lines.append(f"- Gate failed: {', '.join(gate.get('failed', [])) or 'none'}")
    lines.append(f"- Request: {meta.get('request_id')} · {meta.get('latency_ms')} ms")
    lines.append("")
    if not flags:
        lines.append("## No guidance note raised")
        lines.append("")
        lines.append(
            "No deterministic candidate combined with an applicable retrieved clause "
            "survived the gate. This is not certification; it means this pre-review found "
            "no published clause to show you."
        )
        lines.append("")
    for index, flag in enumerate(flags, start=1):
        lines.append(f"## Note {index}: {flag.get('heading')}")
        lines.append("")
        lines.append(f"State: {flag.get('state', 'open')} · the writer decides.")
        lines.append("")
        lines.append("### What code noticed")
        lines.append("")
        for trigger in flag.get("triggers", []):
            label = CLASS_LABEL.get(trigger.get("trigger_class"), trigger.get("trigger_class"))
            matched = trigger.get("matched_text") or ""
            quoted = f' matched "{_line(matched)}"' if matched else ""
            lines.append(f"- **{label}**{quoted}: {_line(trigger.get('rule', ''))}")
        lines.append("")
        lines.append("### Retrieved guidance (Google Agent Search)")
        lines.append("")
        for clause in flag.get("clauses", []):
            lines.append(
                f"- [{clause.get('jurisdiction')}] {clause.get('publisher')}, "
                f"*{clause.get('document_title')}* (v{clause.get('version') or 'n/a'}): "
                f"\"{_line(clause.get('clause', ''))}\" — {clause.get('source_url')}"
            )
        lines.append("")
        agent = flag.get("agent") or {}
        lines.append("### Suggested alternative (Google ADK reviewer)")
        lines.append("")
        lines.append(
            f"Model {agent.get('model', 'n/a')} · safety filter {agent.get('safety_filter', 'n/a')}"
            f" · decision source {agent.get('decision_source', 'n/a')}"
        )
        lines.append("")
        lines.append(str(agent.get("text") or "No alternative was generated."))
        lines.append("")
    document_level = [c for c in candidates if c.get("scene_id") == "document"]
    scene_level_unflagged = [
        c
        for c in candidates
        if c.get("scene_id") != "document"
        and c.get("scene_id") not in {f.get("scene_id") for f in flags}
    ]
    if document_level or scene_level_unflagged:
        lines.append("## Candidates that did not become notes")
        lines.append("")
        for candidate in document_level + scene_level_unflagged:
            label = CLASS_LABEL.get(candidate.get("trigger_class"), candidate.get("trigger_class"))
            lines.append(
                f"- {candidate.get('scene_id')} · {label}: {_line(candidate.get('rule', ''))}"
            )
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "Generated by Duty of Care. Not clinical, legal, compliance, or certification advice. "
        "Sources: WHO, Samaritans, National Action Alliance for Suicide Prevention."
    )
    lines.append("")
    return "\n".join(lines)
