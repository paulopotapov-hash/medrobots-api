from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.contact import Contact
from app.schemas.contact import ContactCreate


def get_by_idempotency_key(session: Session, idempotency_key: str) -> Contact | None:
    return session.scalar(select(Contact).where(Contact.idempotency_key == idempotency_key))


def create_contact(
    session: Session, data: ContactCreate, idempotency_key: str | None = None
) -> Contact:
    contact = Contact(**data.model_dump(), idempotency_key=idempotency_key)
    session.add(contact)
    session.commit()
    session.refresh(contact)
    return contact
