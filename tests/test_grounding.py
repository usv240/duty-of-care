from duty_of_care import grounding
from duty_of_care.models import Scene, Trigger


def trigger(kind: str = "method_specificity") -> Trigger:
    return Trigger(
        scene_id="scene-001",
        trigger_class=kind,
        evidence_excerpt="candidate",
        rule="deterministic rule",
    )


def result(clause_id: str, region: str, classes: list[str]):
    return {
        "document": {
            "id": clause_id,
            "structData": {
                "clause_id": clause_id,
                "jurisdiction": region,
                "publisher": "Publisher",
                "document_title": "Guidance",
                "clause": "Applicable source-linked guidance.",
                "source_url": "https://example.org/guidance",
                "trigger_classes": classes,
                "version": "2026",
                "retrieved_at": "2026-08-20",
            },
        }
    }


def test_search_results_are_filtered_by_jurisdiction_and_trigger(monkeypatch):
    def fake_search(query, page_size):
        assert "method_specificity" in query
        assert page_size == 10
        return [
            result("global", "GLOBAL", ["method_specificity"]),
            result("us", "US", ["method_specificity"]),
            result("gb", "GB", ["method_specificity"]),
            result("wrong-trigger", "US", ["romanticisation"]),
        ]

    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "project")
    monkeypatch.setenv("VERTEX_SEARCH_DATA_STORE", "store")
    monkeypatch.setattr(grounding, "_search", fake_search)
    clauses = grounding.retrieve_clauses(
        Scene(scene_id="scene-001", heading="INT. ROOM", text="scene"),
        [trigger()],
        "US",
    )
    assert [item.clause_id for item in clauses] == ["global", "us"]


def test_no_trigger_means_no_search(monkeypatch):
    def exploding_search(query, page_size):
        raise AssertionError("search must not be called")

    monkeypatch.setattr(grounding, "_search", exploding_search)
    assert grounding.retrieve_clauses(
        Scene(scene_id="scene-001", heading="INT. ROOM", text="scene"), [], "US"
    ) == []


def test_serving_config_uses_explicit_project_id(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "109051079423")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT_ID", "agentic-fleet-2026")
    monkeypatch.setenv("VERTEX_SEARCH_DATA_STORE", "store")
    assert grounding._serving_config().startswith("projects/agentic-fleet-2026/")
