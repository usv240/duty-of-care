from fastapi.testclient import TestClient

from duty_of_care.main import app
from duty_of_care.models import GuidanceClause


def test_landing_page_is_complete_light_default_and_keeps_resources_visible():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "call or text 988" in response.text
    assert "Review against published guidance" in response.text
    assert "prefers-color-scheme" not in response.text
    assert "Overall score" in response.text


def test_grounded_review_runs_agent_but_writer_owns_decision(monkeypatch):
    async def fake_agent(scene, triggers, clauses, operator_id):
        return {
            "status": "completed",
            "model": "gemini-test",
            "text": "A source-grounded explanation.",
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
    data = response.json()["data"]
    assert len(data["grounded_flags"]) == 1
    assert data["grounded_flags"][0]["clauses"][0]["source_url"].startswith("https://")
    assert data["decision_owner"] == "writer"
    assert data["overall_score"] is None
    assert "dismiss" in data["writer_controls"]
