from fastapi.testclient import TestClient

from duty_of_care.main import app
from duty_of_care.models import GuidanceClause


def test_every_page_is_light_by_default_and_keeps_resources_visible():
    client = TestClient(app)
    for path in ("/", "/presets", "/developers", "/stack", "/evidence"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "call or text 988" in response.text, path
        assert "prefers-color-scheme" not in response.text, path
        assert 'src="/static/site.js"' in response.text, path
    landing = client.get("/").text
    assert "Review against published guidance" in landing
    assert "Overall score" in landing
    stylesheet = client.get("/static/site.css").text
    assert "prefers-color-scheme" not in stylesheet


def test_sponsor_stack_ribbon_names_every_tool_on_every_page():
    script = TestClient(app).get("/static/site.js").text
    for key in ("gemini", "adk", "agent_search", "cloudrun", "secret_manager", "cloud_build", "cloud_logging"):
        assert f"['{key}'" in script
    for key in ("replit_agent", "replit_deployment", "replit_auth", "replit_database", "replit_app_storage", "replit_scheduled", "replit_secrets"):
        assert f"['{key}'" in script


def test_grounded_review_runs_agent_but_writer_owns_decision(monkeypatch):
    calls: list[str] = []

    async def fake_agent(scene, triggers, clauses, operator_id, document_level=False):
        calls.append(scene.scene_id)
        assert document_level == (scene.scene_id == "document")
        return {
            "status": "completed",
            "model": "gemini-test",
            "text": "A source-grounded explanation.",
            "safety_filter": "passed",
            "requires_human": True,
        }

    def fake_retrieve(scene, triggers, region):
        return [
            GuidanceClause(
                clause_id="source-clause",
                jurisdiction="US",
                publisher="Publisher",
                document_title="Guidance",
                clause="A cited clause.",
                source_url="https://example.org/guidance",
                trigger_classes=["method_specificity"],
            )
        ]

    monkeypatch.setenv("VERTEX_SEARCH_DATA_STORE", "configured")
    monkeypatch.setattr("duty_of_care.main.retrieve_clauses", fake_retrieve)
    monkeypatch.setattr("duty_of_care.main.explain_grounded_flag", fake_agent)
    response = TestClient(app).post(
        "/v1/review",
        json={
            "screenplay": "INT. ROOM - NIGHT\nA character mentions suicide and an exact amount.",
            "region": "US",
        },
    )
    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    scene_flags = [flag for flag in data["grounded_flags"] if not flag["document_level"]]
    document_flags = [flag for flag in data["grounded_flags"] if flag["document_level"]]
    assert data["grounded_flags"][-1]["document_level"] is True, "the document note reads last"
    assert len(scene_flags) == 1
    assert len(document_flags) == 1  # no resource signpost anywhere in the document
    assert calls == ["scene-001", "document"]  # scene notes first, document note last
    assert scene_flags[0]["clauses"][0]["source_url"].startswith("https://")
    assert data["decision_owner"] == "writer"
    assert data["overall_score"] is None
    assert "dismiss" in data["writer_controls"]
    assert "applicable_clause_retrieved" in body["meta"]["gate"]["passed"]
    assert "resource_signpost_present" in body["meta"]["gate"]["failed"]
    assert body["meta"]["verdict"] == "notes"


def test_review_fails_closed_when_grounding_breaks(monkeypatch):
    def broken_retrieve(scene, triggers, region):
        raise RuntimeError("Agent Search HTTP 503")

    monkeypatch.setenv("VERTEX_SEARCH_DATA_STORE", "configured")
    monkeypatch.setattr("duty_of_care.main.retrieve_clauses", broken_retrieve)
    response = TestClient(app).post("/v1/review", json={"preset_id": "guidance-case"})
    assert response.status_code == 502
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "grounding_failed"
    assert "fabricated" in body["error"]["message"]
