from typing import Dict
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

app = FastAPI(
    title="Call Records Web Service",
    description="A lightweight in-memory call recording service built with FastAPI.",
    version="1.0.0",
)

# In-memory storage: maps call_id -> CallRecord
call_records: Dict[str, "CallRecord"] = {}


class CallRecord(BaseModel):
    """Data model representing an ended call record."""
    call_id: str = Field(..., description="Unique identifier for the call")
    status: str = Field(..., description="Call outcome status (e.g. answered, busy, missed, failed)")
    duration_secs: int = Field(..., ge=0, description="Duration of the call in seconds (must be non-negative)")

    @field_validator("call_id")
    @classmethod
    def validate_call_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Field 'call_id' cannot be empty or whitespace.")
        return value.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Field 'status' cannot be empty or whitespace.")
        return value.strip()


class CallResponse(BaseModel):
    """Response model for POST /call-ended endpoint."""
    message: str = Field(..., description="Status message indicating processing result")
    record: CallRecord = Field(..., description="The stored call record")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Format request validation errors with clear, human-readable messages.
    Returns HTTP 400 Bad Request if required fields (like call_id) are missing or invalid.
    """
    errors = exc.errors()

    for err in errors:
        loc = err.get("loc", ())
        if "call_id" in loc:
            err_type = err.get("type", "")
            err_msg = err.get("msg", "")
            if "missing" in err_type or "Field required" in err_msg:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Field 'call_id' is required."},
                )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Invalid 'call_id': {err_msg}"},
            )

    # Clear message for other field validation issues
    if errors:
        first_err = errors[0]
        field_name = ".".join(str(l) for l in first_err.get("loc", ()) if l != "body")
        msg = first_err.get("msg", "Invalid input")
        detail_msg = f"Field '{field_name}': {msg}" if field_name else msg
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": detail_msg},
        )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Invalid request payload."},
    )


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint providing service info."""
    return {
        "status": "healthy",
        "service": "Call Records Service",
        "total_calls_stored": len(call_records),
    }


@app.post("/call-ended", response_model=CallResponse, status_code=status.HTTP_200_OK, tags=["Calls"])
async def record_call_ended(record: CallRecord):
    """
    Record an ended call event.

    - Stores the call record in memory.
    - For an already existing call_id, does not create or overwrite a record and returns
      HTTP 200 with an explicit message indicating the call was already processed.
    - A request without call_id is rejected with a clear error message.
    """
    if record.call_id in call_records:
        return CallResponse(
            message="Call record already processed.",
            record=call_records[record.call_id],
        )

    call_records[record.call_id] = record
    return CallResponse(
        message="Call record stored successfully.",
        record=record,
    )


@app.get("/calls/{call_id}", response_model=CallRecord, tags=["Calls"])
async def get_call_record(call_id: str):
    """
    Retrieve a stored call record by its call_id.

    - Returns the stored record if found.
    - Returns HTTP 404 with a clear message if the call does not exist.
    """
    clean_id = call_id.strip()
    record = call_records.get(clean_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call record with call_id '{clean_id}' was not found.",
        )

    return record
