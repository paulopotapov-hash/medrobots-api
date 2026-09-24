from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.contact import Contact
from app.repositories.contact_repository import create_contact, get_by_idempotency_key
from app.schemas.contact import ContactCreate


def submit_contact(
    session: Session, data: ContactCreate, idempotency_key: str | None = None
) -> Contact:
    """Persist a contact request.

    When the client sends an Idempotency-Key, a retried POST (double click,
    client timeout, network retry) returns the original contact instead of
    creating a duplicate. Without a key, every request creates a new row, as
    before.
    """
    if idempotency_key is not None:
        existing = get_by_idempotency_key(session, idempotency_key)
        if existing is not None:
            return existing
        try:
            return create_contact(session, data, idempotency_key)
        except IntegrityError:
            # Two requests with the same key raced past the check above;
            # the unique constraint caught it. The insert failed, so the
            # session is left in a failed transaction state that must be
            # rolled back before it can be used again.
            session.rollback()
            existing = get_by_idempotency_key(session, idempotency_key)
            if existing is not None:
                return existing
            raise
    return create_contact(session, data)
