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
    assert data["message"] == "Call record stored successfully."
    assert data["record"]["call_id"] == "abc123"
    assert data["record"]["status"] == "answered"
    assert data["record"]["duration_secs"] == 42
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


def test_duplicate_call_id_exact_payload(client):
    """
    Test duplicate handling when sending the exact same payload twice:
    - Both return HTTP 200.
    - Second response indicates the call was already processed.
    - Only one record exists for the call_id.
    - Stored record remains identical to the original payload.
    - Unrelated second call record is not affected.
    """
    # 1. Store first call record
    payload_1 = {
        "call_id": "call-001",
        "status": "answered",
        "duration_secs": 42,
    }
    res1 = client.post("/call-ended", json=payload_1)
    assert res1.status_code == 200
    assert res1.json()["message"] == "Call record stored successfully."
    assert res1.json()["record"] == payload_1

    # 2. Store an unrelated second call record
    payload_2 = {
        "call_id": "call-002",
        "status": "missed",
        "duration_secs": 0,
    }
    res_unrelated = client.post("/call-ended", json=payload_2)
    assert res_unrelated.status_code == 200
    assert len(call_records) == 2

    # 3. Send the exact same payload twice using the same call_id (call-001)
    res2 = client.post("/call-ended", json=payload_1)

    # Assert both requests return HTTP 200
    assert res2.status_code == 200

    # Assert that the second response indicates the call was already processed
    data2 = res2.json()
    assert "already processed" in data2["message"].lower()
    assert data2["record"] == payload_1

    # Assert that no second record was created (total store size remains 2)
    assert len(call_records) == 2

    # Assert that the stored record remains identical to the original payload
    get_res1 = client.get("/calls/call-001")
    assert get_res1.status_code == 200
    assert get_res1.json() == payload_1

    # Assert that unrelated second call record is not affected
    get_res2 = client.get("/calls/call-002")
    assert get_res2.status_code == 200
    assert get_res2.json() == payload_2


def test_duplicate_call_id_conflicting_payload_does_not_overwrite(client):
    """
    Test that submitting a different payload with an existing call_id
    does not overwrite the stored record and returns HTTP 200 indicating already processed.
    """
    original_payload = {
        "call_id": "dup-conflict",
        "status": "answered",
        "duration_secs": 42,
    }
    res1 = client.post("/call-ended", json=original_payload)
    assert res1.status_code == 200

    # Attempt to post a different payload with the same call_id
    different_payload = {
        "call_id": "dup-conflict",
        "status": "busy",
        "duration_secs": 999,
    }
    res2 = client.post("/call-ended", json=different_payload)
    assert res2.status_code == 200
    assert "already processed" in res2.json()["message"].lower()
    assert res2.json()["record"] == original_payload

    # Stored record must remain unchanged
    get_res = client.get("/calls/dup-conflict")
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
