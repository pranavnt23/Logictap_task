import pytest
from fastapi.testclient import TestClient
from main import app, call_records


@pytest.fixture(autouse=True)
def clean_records():
    """Ensure in-memory call records are cleared before each test."""
    call_records.clear()
    yield
    call_records.clear()


@pytest.fixture
def client():
    """Create a FastAPI test client instance."""
    return TestClient(app)


def test_post_call_ended_success(client):
    """Test standard successful POST /call-ended request."""
    payload = {
        "call_id": "abc123",
        "status": "answered",
        "duration_secs": 42,
    }
    response = client.post("/call-ended", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["call_id"] == "abc123"
    assert data["status"] == "answered"
    assert data["duration_secs"] == 42
    assert len(call_records) == 1


def test_get_call_success(client):
    """Test retrieving an existing call record via GET /calls/{call_id}."""
    payload = {
        "call_id": "call-999",
        "status": "completed",
        "duration_secs": 120,
    }
    post_res = client.post("/call-ended", json=payload)
    assert post_res.status_code == 200

    get_res = client.get("/calls/call-999")
    assert get_res.status_code == 200
    assert get_res.json() == payload


def test_duplicate_call_id_does_not_create_second_record(client):
    """
    Test that submitting the same call_id again does not create a second record
    and still returns a successful response with the original record preserved.
    """
    initial_payload = {
        "call_id": "dup-test-01",
        "status": "answered",
        "duration_secs": 42,
    }
    res1 = client.post("/call-ended", json=initial_payload)
    assert res1.status_code == 200
    assert len(call_records) == 1

    # Attempt to post a different payload with the same call_id
    second_payload = {
        "call_id": "dup-test-01",
        "status": "busy",
        "duration_secs": 999,
    }
    res2 = client.post("/call-ended", json=second_payload)
    assert res2.status_code == 200

    # Ensure no second record was created
    assert len(call_records) == 1

    # Ensure original record was preserved (idempotency)
    assert res2.json()["status"] == "answered"
    assert res2.json()["duration_secs"] == 42

    # Verify via GET as well
    get_res = client.get("/calls/dup-test-01")
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "answered"
    assert get_res.json()["duration_secs"] == 42


def test_post_without_call_id_rejected(client):
    """Test that a request missing call_id is rejected with a clear error message."""
    payload = {
        "status": "answered",
        "duration_secs": 42,
    }
    response = client.post("/call-ended", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "call_id" in data["detail"].lower()
    assert "required" in data["detail"].lower()
    assert len(call_records) == 0


def test_post_with_blank_call_id_rejected(client):
    """Test that a request with empty or whitespace-only call_id is rejected."""
    payload = {
        "call_id": "   ",
        "status": "answered",
        "duration_secs": 42,
    }
    response = client.post("/call-ended", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "call_id" in data["detail"].lower()
    assert len(call_records) == 0


def test_post_with_empty_json_rejected(client):
    """Test that an empty JSON body is rejected with a clear error message."""
    response = client.post("/call-ended", json={})

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "call_id" in data["detail"].lower()


def test_get_nonexistent_call_returns_404(client):
    """Test that GET /calls/{call_id} returns HTTP 404 with a clear message when not found."""
    response = client.get("/calls/nonexistent-call-id")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "nonexistent-call-id" in data["detail"]
    assert "not found" in data["detail"].lower()


def test_post_negative_duration_rejected(client):
    """Test that negative duration_secs is rejected."""
    payload = {
        "call_id": "neg-test",
        "status": "answered",
        "duration_secs": -10,
    }
    response = client.post("/call-ended", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert "duration_secs" in data["detail"]


def test_root_endpoint_health(client):
    """Test service health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
