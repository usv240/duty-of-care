"""When this host proxies to the Cloud Run backend, health and stack tell the truth about both sides."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from duty_of_care import main, replit_platform
from duty_of_care.main import app


@pytest.fixture(autouse=True)
def _surface(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("DUTY_OF_CARE_BACKEND_URL", "https://backend.example")
    monkeypatch.delenv("VERTEX_SEARCH_DATA_STORE", raising=False)
    monkeypatch.setenv("REPL_ID", "abc")
    monkeypatch.setenv("REPLIT_DEPLOYMENT", "1")
    monkeypatch.setenv("REPLIT_DOMAINS", "duty-of-care.replit.app")
    monkeypatch.setenv("DUTY_OF_CARE_STATE_DIR", str(tmp_path))
    replit_platform.reset_stores()
    yield
    replit_platform.reset_stores()


def test_health_reads_google_from_backend_and_replit_locally(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch(path: str):
        assert path == "/health/integrations"
        return {"data": {"integrations": {"google_vertex": {"ok": True}, "agent_search": {"ok": True}, "google_adk": {"ok": True}}}}

    monkeypatch.setattr(main, "_fetch_backend_json", fake_fetch)
    body = TestClient(app).get("/health").json()
    assert body["product_surface"] == "replit"
    assert body["integrations"]["google_vertex"] == {"ok": True, "via": "backend"}
    assert body["integrations"]["replit"]["host"] == "duty-of-care.replit.app"
    assert body["integrations"]["backend"]["ok"] is True


def test_stack_merges_backend_google_group_with_local_replit_group(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch(path: str):
        if path == "/health/integrations":
            return {"data": {"integrations": {"google_vertex": {"ok": True}, "agent_search": {"ok": True}, "google_adk": {"ok": True}}}}
        return {"data": {"surface": "cloud_run", "components": [
            {"key": "gemini", "group": "google", "status": "live", "evidence": "probe"},
            {"key": "replit_deployment", "group": "partner", "status": "pending"},
        ]}}

    monkeypatch.setattr(main, "_fetch_backend_json", fake_fetch)
    data = TestClient(app).get("/v1/stack").json()["data"]
    components = {c["key"]: c for c in data["components"]}
    assert components["gemini"]["status"] == "live"
    assert "reported by the Cloud Run backend" in components["gemini"]["evidence"]
    assert components["replit_deployment"]["status"] == "active"
    assert "duty-of-care.replit.app" in components["replit_deployment"]["evidence"]
    assert data["surface"] == "replit"
    assert data["backend"]["url"] == "https://backend.example"


def test_health_reports_unreachable_backend_honestly(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(path: str):
        raise TimeoutError("no answer")

    monkeypatch.setattr(main, "_fetch_backend_json", broken)
    body = TestClient(app).get("/health").json()
    assert body["integrations"]["google_vertex"]["ok"] is False
    assert body["integrations"]["backend"]["ok"] is False
    assert body["agent_runtime_ready"] is False


def test_export_falls_back_when_primary_store_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class Broken:
        backend = "replit_app_storage"

        def put(self, name, text):
            raise RuntimeError("no bucket")

        def get(self, export_id):
            return None

    monkeypatch.setattr(replit_platform, "export_store", lambda: Broken())
    client = TestClient(app)
    created = client.post("/v1/exports", json={"title": "t", "review": {"disclaimer": "d"}, "meta": {}}).json()["data"]
    assert created["backend"] == "local_file"
    assert "replit_app_storage failed" in created["note"]
    assert client.get(created["url"]).status_code == 200
