from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.contact import ContactCreate, ContactCreated
from app.schemas.error import ErrorResponse
from app.services.contact_service import submit_contact

router = APIRouter(tags=["Contacts"])

# Validated by FastAPI/Pydantic as part of request parsing (pattern= on the
# Header), so a malformed key fails the same way as an invalid body field:
# 422 with the shared "validation_error" envelope, via the
# RequestValidationError handler in app.main. No separate error path needed.
_IDEMPOTENCY_KEY_PATTERN = r"^[A-Za-z0-9_-]{1,255}$"


@router.post(
    "/contacts",
    response_model=ContactCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a contact request",
    description=(
        "Validates and stores a contact request for later handling by Med Robots. "
        "An optional Idempotency-Key header makes retried submissions (double "
        "click, client timeout, network retry) safe: repeating the same key "
        "returns the original contact instead of creating a duplicate."
    ),
    responses={
        413: {"description": "Request body too large", "model": ErrorResponse},
        422: {"description": "Invalid request data", "model": ErrorResponse},
        429: {"description": "Too many requests", "model": ErrorResponse},
        500: {"description": "Unexpected server error", "model": ErrorResponse},
        503: {"description": "Database unavailable", "model": ErrorResponse},
    },
)
@limiter.limit("5/minute")
def submit(
    request: Request,
    data: ContactCreate,
    session: Annotated[Session, Depends(get_db)],
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            pattern=_IDEMPOTENCY_KEY_PATTERN,
            description=(
                "Optional client-generated token. Retrying a POST with the same "
                "key returns the original contact instead of creating a new one."
            ),
        ),
    ] = None,
) -> ContactCreated:
    return ContactCreated.model_validate(submit_contact(session, data, idempotency_key))
