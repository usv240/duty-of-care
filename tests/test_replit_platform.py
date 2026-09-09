"""Replit adapters must fall back honestly and never trust identity off-platform."""

from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

from duty_of_care import replit_platform
from duty_of_care.main import app


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DUTY_OF_CARE_STATE_DIR", str(tmp_path))
    for name in ("REPL_ID", "REPLIT_DEPLOYMENT", "DATABASE_URL", "REPLIT_DB_URL", "DUTY_OF_CARE_TRUST_AUTH_HEADERS"):
        monkeypatch.delenv(name, raising=False)
    replit_platform.reset_stores()
    yield
    replit_platform.reset_stores()


def test_identity_headers_are_ignored_off_replit() -> None:
    assert replit_platform.identity_from_headers({"X-Replit-User-Id": "u1"}) is None


def test_identity_headers_are_trusted_on_replit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPL_ID", "abc")
    identity = replit_platform.identity_from_headers({"x-replit-user-id": "u1", "x-replit-user-name": "Mara"})
    assert identity is not None
    assert identity.provider == "replit_auth"
    assert identity.name == "Mara"


def test_decisions_require_sign_in_and_never_store_screenplay(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app)
    anonymous = client.post("/v1/decisions", json={"flag_id": "f", "scene_id": "s", "heading": "h", "decision": "dismissed"})
    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "sign_in_required"

    monkeypatch.setenv("DUTY_OF_CARE_TRUST_AUTH_HEADERS", "1")
    headers = {"X-Replit-User-Id": "writer-1"}
    saved = client.post(
        "/v1/decisions",
        json={"flag_id": "f", "scene_id": "s", "heading": "INT. ROOM", "decision": "dismissed", "reason": "intent", "scene_text": "secret draft"},
        headers=headers,
    )
    assert saved.status_code == 200
    record = saved.json()["data"]["decision"]
    assert "secret draft" not in saved.text
    assert record["scene_fingerprint"]
    listed = client.get("/v1/decisions", headers=headers).json()["data"]
    assert listed["backend"] == "local_file"
    assert [item["decision_id"] for item in listed["decisions"]] == [record["decision_id"]]
    assert listed["stale"] == []
    assert client.delete(f"/v1/decisions/{record['decision_id']}", headers=headers).status_code == 200
    assert client.get("/v1/decisions", headers=headers).json()["data"]["decisions"] == []


def test_export_is_explicit_and_round_trips() -> None:
    client = TestClient(app)
    created = client.post("/v1/exports", json={"title": "t", "review": {"disclaimer": "d"}, "meta": {}})
    assert created.status_code == 200
    data = created.json()["data"]
    assert data["backend"] == "local_file"
    fetched = client.get(data["url"])
    assert fetched.status_code == 200
    assert "attachment" in fetched.headers["content-disposition"]
    assert client.post("/v1/exports", json={"title": "t", "review": {}}).status_code == 422
    assert client.get("/v1/exports/exp_missing").status_code == 404


def test_replit_database_backend_is_selected_and_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakePostgresStore(replit_platform.FileDecisionStore):
        backend = "replit_postgres"

        def __init__(self, dsn: str) -> None:
            assert dsn == "postgresql://managed-replit-database"
            super().__init__(tmp_path / "managed-database.json")

    monkeypatch.setenv("REPL_ID", "abc")
    monkeypatch.setenv("DATABASE_URL", "postgresql://managed-replit-database")
    monkeypatch.setattr(replit_platform, "PostgresDecisionStore", FakePostgresStore)
    replit_platform.reset_stores()
    store = replit_platform.decision_store()
    record = {"decision_id": "dec_1", "decision": "dismissed"}
    store.put("writer-1", record)
    assert store.backend == "replit_postgres"
    assert store.list("writer-1") == [record]


def test_replit_app_storage_backend_is_selected_and_round_trips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blobs: dict[str, str] = {}

    class FakeClient:
        def upload_from_text(self, path: str, text: str) -> None:
            blobs[path] = text

        def download_as_text(self, path: str) -> str:
            return blobs[path]

    package = ModuleType("replit")
    package.__path__ = []  # type: ignore[attr-defined]
    object_storage = ModuleType("replit.object_storage")
    object_storage.Client = FakeClient  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "replit", package)
    monkeypatch.setitem(sys.modules, "replit.object_storage", object_storage)
    monkeypatch.setenv("REPL_ID", "abc")
    replit_platform.reset_stores()
    store = replit_platform.export_store()
    export_id = store.put("review", '{"disclaimer":"present"}')
    assert store.backend == "replit_app_storage"
    assert store.get(export_id) == '{"disclaimer":"present"}'


def test_scheduled_recheck_records_metadata_only(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.json"
    corpus.write_text("[]", "utf-8")
    first = replit_platform.record_scheduled_recheck(corpus_path=corpus, backend_health={"agent_runtime_ready": True, "product_surface": "cloud_run_fallback"})
    assert first["runs"] == 1 and first["corpus_changed_since_last_run"] is False
    corpus.write_text("[1]", "utf-8")
    second = replit_platform.record_scheduled_recheck(corpus_path=corpus, backend_health={})
    assert second["runs"] == 2 and second["corpus_changed_since_last_run"] is True
    assert replit_platform.capabilities()["scheduled"]["ok"] is True


def test_stack_reports_replit_agent_pending_until_owner_records_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr("duty_of_care.main._live_integrations", _fake_integrations)
    components = {c["key"]: c for c in client.get("/v1/stack").json()["data"]["components"]}
    assert components["replit_agent"]["status"] == "pending"
    assert components["replit_deployment"]["status"] == "pending"
    monkeypatch.setenv("DUTY_OF_CARE_REPLIT_AGENT_EVIDENCE_URL", "https://example.org/transcript")
    monkeypatch.setenv("DUTY_OF_CARE_REPLIT_AGENT_COMMIT", "abcdef1234567890")
    components = {c["key"]: c for c in client.get("/v1/stack").json()["data"]["components"]}
    assert components["replit_agent"]["status"] == "active"


async def _fake_integrations() -> dict[str, dict[str, object]]:
    return {
        "google_vertex": {"ok": True, "model": "gemini-test"},
        "agent_search": {"ok": True, "document_id": "doc"},
        "google_adk": {"ok": True},
        "api_keys": {"ok": False},
        "replit": {"ok": False, "host": None, "deployment": False},
    }


def test_app_storage_card_is_earned_by_a_write_not_by_a_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Constructing the client proves a library; only a landed write proves a bucket."""

    class Unreachable:
        backend = "replit_app_storage"

        def put(self, name, text):
            raise ConnectionError("no bucket")

        def get(self, export_id):
            return None

    monkeypatch.setenv("REPL_ID", "abc")
    monkeypatch.setattr(replit_platform, "export_store", lambda: Unreachable())
    replit_platform._LAST_EXPORT.update(backend=None, note=None)
    assert replit_platform.capabilities()["object_storage"]["proven"] is False

    export_id, backend, note = replit_platform.put_export("t", "{}")
    assert backend == "local_file" and "ConnectionError" in note
    caps = replit_platform.capabilities()["object_storage"]
    assert caps["proven"] is False
    assert "stored locally instead" in caps["detail"]


def test_app_storage_card_turns_active_after_a_landed_write(monkeypatch: pytest.MonkeyPatch) -> None:
    class Working:
        backend = "replit_app_storage"

        def put(self, name, text):
            return "exp_ok"

        def get(self, export_id):
            return "{}"

    monkeypatch.setenv("REPL_ID", "abc")
    monkeypatch.setattr(replit_platform, "export_store", lambda: Working())
    replit_platform._LAST_EXPORT.update(backend=None, note=None)
    export_id, backend, note = replit_platform.put_export("t", "{}")
    assert (export_id, backend, note) == ("exp_ok", "replit_app_storage", None)
    assert replit_platform.capabilities()["object_storage"]["proven"] is True
