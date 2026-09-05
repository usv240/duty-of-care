from __future__ import annotations

from fastapi.testclient import TestClient

from duty_of_care.main import app
from duty_of_care.presets import all_presets
from duty_of_care.report import render_markdown
from duty_of_care.triggers import DOCUMENT_SCENE_ID, detect_triggers


def test_every_preset_matches_its_stated_expectation() -> None:
    """The library must not promise a demo the deterministic layer cannot deliver."""
    for preset in all_presets():
        classes = {item.trigger_class for item in detect_triggers(preset.text)}
        assert classes == set(preset.expected_trigger_classes), preset.id
        scene_level = {
            item.scene_id for item in detect_triggers(preset.text) if item.scene_id != DOCUMENT_SCENE_ID
        }
        assert bool(scene_level or classes) == preset.expect_flag, preset.id


def test_presets_are_listed_viewable_and_downloadable() -> None:
    client = TestClient(app)
    listing = client.get("/v1/presets").json()["data"]
    assert listing["count"] >= 6
    first = listing["presets"][0]
    assert "text" not in first
    assert set(first["downloads"]) == {"fountain", "txt", "json"}
    full = client.get(f"/v1/presets/{first['id']}").json()["data"]
    assert full["text"].startswith(("INT.", "EXT."))
    for fmt in ("fountain", "txt", "json"):
        response = client.get(f"/v1/presets/{first['id']}/download?format={fmt}")
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
    assert client.get("/v1/presets/missing").status_code == 404
    assert client.get(f"/v1/presets/{first['id']}/download?format=pdf").status_code == 400


def test_review_accepts_preset_id_and_returns_gate_meta() -> None:
    response = TestClient(app).post("/v1/review", json={"preset_id": "guidance-case"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["disclaimer"]
    assert body["data"]["overall_score"] is None
    assert "deterministic_candidate_present" in body["meta"]["gate"]["passed"]
    assert "grounding_available" in body["meta"]["gate"]["failed"]
    assert body["meta"]["abstained_because"]


def test_markdown_report_leads_with_disclaimer_and_resources() -> None:
    client = TestClient(app)
    response = client.post("/v1/review?format=markdown", json={"preset_id": "guidance-case"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    text = response.text
    assert text.index("not clinical or professional certification") < text.index("## Summary")
    assert "988" in text
    rendered = client.post(
        "/v1/report",
        json={"title": "x", "review": {"disclaimer": "d", "resources": [], "scenes": [], "grounded_flags": [], "trigger_candidates": []}, "meta": {"request_id": "req_1"}},
    )
    assert rendered.status_code == 200
    assert "No guidance note raised" in rendered.text
    assert client.post("/v1/report", json={"review": {}}).status_code == 422


def test_render_markdown_never_certifies() -> None:
    text = render_markdown({"disclaimer": "d", "resources": [], "grounded_flags": []}, {})
    assert "safe" not in text.lower().replace("unsafe", "")


def test_eval_endpoint_serves_live_benchmark_with_failures_listed() -> None:
    data = TestClient(app).get("/v1/eval/latest").json()["data"]
    assert data["cases"] == 48
    assert data["counts"]["true_positive"] + data["counts"]["false_negative"] == 24
    assert data["independent_review"]["status"] == "pending"
    assert isinstance(data["failures"], list)
