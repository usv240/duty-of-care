"""Keys raise limits without ever becoming a gate."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from duty_of_care import apikeys
from duty_of_care.main import app

SECRET = "test-signing-secret-not-a-real-one"


@pytest.fixture(name="secret")
def _secret(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv(apikeys.SECRET_ENV, SECRET)
    return SECRET


def test_minted_key_verifies(secret: str) -> None:
    issued = apikeys.mint()
    identity = apikeys.verify(str(issued["api_key"]))
    assert identity.is_keyed
    assert identity.key_id == issued["key_id"]


def test_no_credential_is_anonymous_not_an_error(secret: str) -> None:
    assert apikeys.identify(None, None).tier == apikeys.ANONYMOUS_TIER


def test_tampered_key_is_rejected(secret: str) -> None:
    token = str(apikeys.mint()["api_key"])
    with pytest.raises(apikeys.ApiKeyError, match="signature"):
        apikeys.verify(token[:-1] + ("0" if token[-1] != "0" else "1"))


def test_wrong_scheme_is_an_error(secret: str) -> None:
    with pytest.raises(apikeys.ApiKeyError, match="Bearer"):
        apikeys.identify("Basic abc", None)


def test_judge_can_mint_and_use_a_key_without_email(secret: str) -> None:
    client = TestClient(app)
    minted = client.post("/v1/keys")
    assert minted.status_code == 200
    key = minted.json()["data"]["api_key"]
    assert key.startswith("doc_")
    described = client.get("/v1/keys/self", headers={"Authorization": f"Bearer {key}"})
    assert described.json()["data"]["tier"] == "keyed"
    assert described.json()["data"]["limits_per_minute"]["review"] == 30


def test_anonymous_review_still_works_when_keys_are_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(apikeys.SECRET_ENV, raising=False)
    client = TestClient(app)
    assert client.post("/v1/keys").status_code == 503
    review = client.post("/v1/review", json={"preset_id": "responsible-depiction"})
    assert review.status_code == 200
    assert review.json()["meta"]["caller"]["tier"] == "anonymous"


def test_broken_key_is_a_401_with_a_fix(secret: str) -> None:
    response = TestClient(app).post(
        "/v1/review", json={"preset_id": "responsible-depiction"}, headers={"X-API-Key": "doc_bad"}
    )
    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_api_key"
    assert "/v1/keys" in body["error"]["fix"]
