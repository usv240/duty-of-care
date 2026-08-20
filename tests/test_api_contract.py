from fastapi.testclient import TestClient

from duty_of_care.main import app


def test_disclaimer_and_resources_are_always_present():
    response = TestClient(app).post("/v1/review", json={"screenplay":"INT. ROOM - NIGHT\nA character mentions self-harm.","region":"US"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["disclaimer"]
    assert data["resources"]
    assert data["grounded_flags"] == []
    assert data["grounding_status"] == "not_configured"
