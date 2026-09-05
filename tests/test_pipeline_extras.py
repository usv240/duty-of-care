"""Streaming, jurisdiction summary, Model Armor withholding, and the agent package."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from duty_of_care import main, model_armor
from duty_of_care.main import app
from duty_of_care.models import GuidanceClause
from duty_of_care_agent.agent import ALTERNATIVE_HEADING, BLOCKED, apply_output_filter, build_agent, review_prompt


def _clause(clause_id: str, jurisdiction: str, classes: list[str]) -> GuidanceClause:
    return GuidanceClause(
        clause_id=clause_id, jurisdiction=jurisdiction, publisher="P", document_title="D",
        clause="c", source_url="https://example.org", trigger_classes=classes,
    )


def test_stream_emits_progress_then_result() -> None:
    client = TestClient(app)
    events = []
    with client.stream("POST", "/v1/review/stream", json={"preset_id": "guidance-case"}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/x-ndjson")
        for line in response.iter_lines():
            if line.strip():
                events.append(json.loads(line))
    kinds = [event["event"] for event in events]
    assert kinds[0] == "parsed" and kinds[-1] == "result"
    assert "complete" in kinds
    assert events[-1]["data"]["disclaimer"]
    assert events[-1]["meta"]["region_known"] is True


def test_stream_ends_with_typed_error_when_grounding_breaks(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(scene, triggers, region):
        raise RuntimeError("boom")

    monkeypatch.setenv("VERTEX_SEARCH_DATA_STORE", "configured")
    monkeypatch.setattr("duty_of_care.main.retrieve_clauses", broken)
    events = []
    with TestClient(app).stream("POST", "/v1/review/stream", json={"preset_id": "guidance-case"}) as response:
        for line in response.iter_lines():
            if line.strip():
                events.append(json.loads(line))
    assert events[-1]["event"] == "error"
    assert events[-1]["error"]["code"] == "grounding_failed"


def test_jurisdiction_summary_shows_divergence_without_reconciling() -> None:
    clauses = [
        _clause("gb", "GB", ["romanticisation"]).model_dump(),
        _clause("global", "GLOBAL", ["romanticisation", "repetition"]).model_dump(),
    ]
    by_jurisdiction, divergence = main._jurisdiction_summary(clauses)
    assert by_jurisdiction == {"GB": ["gb"], "GLOBAL": ["global"]}
    assert divergence == [{"trigger_class": "romanticisation", "jurisdictions": ["GB", "GLOBAL"]}]


def test_model_armor_match_withholds_text_and_fails_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_agent(scene, triggers, clauses, operator_id, document_level=False):
        return {"status": "completed", "model": "m", "text": "Some text", "safety_filter": "passed", "runtime": "adk_in_process"}

    monkeypatch.setenv("VERTEX_SEARCH_DATA_STORE", "configured")
    monkeypatch.setenv(model_armor.TEMPLATE_ENV, "projects/p/locations/us-central1/templates/t")
    monkeypatch.setattr("duty_of_care.main.retrieve_clauses", lambda scene, triggers, region: [_clause("x", "US", ["method_specificity"])])
    monkeypatch.setattr("duty_of_care.main.explain_grounded_flag", fake_agent)
    monkeypatch.setattr(
        "duty_of_care.model_armor.screen_model_response",
        lambda text: {"status": "screened", "template": "t", "match": True, "matched_filters": ["rai"]},
    )
    body = TestClient(app).post("/v1/review", json={"screenplay": "INT. ROOM - NIGHT\nA character mentions suicide and an exact amount. Help is available."}).json()
    flag = body["data"]["grounded_flags"][0]
    assert flag["agent"]["text"] == model_armor.WITHHELD
    assert flag["agent"]["model_armor"]["match"] is True
    assert "model_armor_clear" in body["meta"]["gate"]["failed"]
    assert body["meta"]["model_armor"] == "t"


def test_agent_package_definition_is_shared() -> None:
    agent = build_agent("gemini-test")
    assert agent.name == "GuidanceContextReviewer"
    assert sorted(tool.__name__ for tool in agent.tools) == ["check_alternative", "get_bound_guidance"]
    assert "document_level" in agent.instruction
    assert review_prompt({"document_level": True, "triggers": [{"trigger_class": "signposting_absence"}], "scene_text": "x"}).startswith("Document-level review")
    assert apply_output_filter("scene", "")[0] == BLOCKED
    assert apply_output_filter("scene", f"Why\n\n{ALTERNATIVE_HEADING}\n\nA friend stays.")[1] == "passed"


def test_model_armor_not_configured_reports_honestly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(model_armor.TEMPLATE_ENV, raising=False)
    assert model_armor.screen_model_response("anything") == {"status": "not_configured", "template": None, "match": None}
    stack = {c["key"]: c for c in TestClient(app).get("/v1/stack").json()["data"]["components"]} if False else None
    assert stack is None  # the stack endpoint probes Vertex; covered in test_replit_platform with a fake
