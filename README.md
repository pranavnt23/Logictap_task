# Call Records Web Service

A lightweight, clean in-memory call recording web service built with [FastAPI](https://fastapi.tiangolo.com/) and [Pydantic](https://docs.pydantic.dev/).

---

## Features & Implementation Details

- **In-Memory Storage**: Uses a Python in-memory dictionary `call_records` to store records by `call_id` without external database dependencies.
- **`POST /call-ended`**:
  - Accepts call records in JSON format: `{"call_id": "...", "status": "...", "duration_secs": ...}`.
  - **Idempotency**: If the same `call_id` is submitted again, it preserves the existing record without creating a second record, returning a successful `200 OK` response.
  - **Clear Validation**: Rejects requests missing `call_id` or with empty/invalid inputs with a clear error message and `HTTP 400 Bad Request`.
- **`GET /calls/{call_id}`**:
  - Retrieves the stored record for the given `call_id`.
  - Returns `HTTP 404 Not Found` with a clear message if the call ID does not exist.
- **Automated Tests**: Comprehensive pytest test suite covering all requirements and edge cases.

---

## Project Structure

```text
Logictap_task/
├── main.py          # FastAPI application & endpoints
├── test_main.py     # Automated unit and integration tests
├── requirements.txt # Project dependencies
└── README.md        # Documentation and curl examples
```

---

## 1. Setup & Installation

### Prerequisites
- Python 3.10+ (tested on Python 3.10+)

### Create & Activate Virtual Environment (Recommended)

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 2. Running the Server

Start the FastAPI application using Uvicorn:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The server will be available at:
- **Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **Alternative ReDoc UI**: `http://127.0.0.1:8000/redoc`

---

## 3. Example `curl` Commands

### 1. Record a New Call (`POST /call-ended`)

```bash
curl -X POST "http://127.0.0.1:8000/call-ended" \
  -H "Content-Type: application/json" \
  -d "{\"call_id\": \"abc123\", \"status\": \"answered\", \"duration_secs\": 42}"
```

**Response (HTTP 200 OK):**
```json
{
  "call_id": "abc123",
  "status": "answered",
  "duration_secs": 42
}
```

---

### 2. Retrieve Stored Call (`GET /calls/{call_id}`)

```bash
curl -X GET "http://127.0.0.1:8000/calls/abc123"
```

**Response (HTTP 200 OK):**
```json
{
  "call_id": "abc123",
  "status": "answered",
  "duration_secs": 42
}
```

---

### 3. Duplicate Call Submission (`POST /call-ended`)

If submitted again with the same `call_id`, no duplicate record is created and the server returns the existing record successfully:

```bash
curl -X POST "http://127.0.0.1:8000/call-ended" \
  -H "Content-Type: application/json" \
  -d "{\"call_id\": \"abc123\", \"status\": \"busy\", \"duration_secs\": 99}"
```

**Response (HTTP 200 OK):**
```json
{
  "call_id": "abc123",
  "status": "answered",
  "duration_secs": 42
}
```

---

### 4. Missing `call_id` Rejected (`POST /call-ended`)

Requests omitting `call_id` are rejected with a clear error message:

```bash
curl -X POST "http://127.0.0.1:8000/call-ended" \
  -H "Content-Type: application/json" \
  -d "{\"status\": \"answered\", \"duration_secs\": 42}"
```

**Response (HTTP 400 Bad Request):**
```json
{
  "detail": "Field 'call_id' is required."
}
```

---

### 5. Call Not Found (`GET /calls/{call_id}`)

Requesting a non-existent `call_id` returns HTTP 404:

```bash
curl -X GET "http://127.0.0.1:8000/calls/nonexistent_call"
```

**Response (HTTP 404 Not Found):**
```json
{
  "detail": "Call record with call_id 'nonexistent_call' was not found."
}
```

---

## 4. Running Automated Tests

Run the test suite using `pytest`:

```bash
pytest test_main.py -v
```
