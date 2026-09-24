from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Only "new" is produced by this API today. "in_progress" and "resolved" are
# reserved for a future internal handling flow (no admin endpoints exist yet
# to set them); the constraint exists so the column stays consistent as that
# flow is added later.
CONTACT_STATUSES = ("new", "in_progress", "resolved")


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        CheckConstraint(f"status IN {CONTACT_STATUSES!r}", name="ck_contacts_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))
    address: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="new")
    # Client-supplied token (Idempotency-Key header) used to make retried
    # POSTs safe. NULL for clients that do not send one; unique when present
    # so a second request with the same key can never create a second row.
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
