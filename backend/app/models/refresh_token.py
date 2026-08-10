import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One issued refresh token.

    Opaque and random rather than a JWT, because the whole point of this table
    is that a session can be *revoked*. A self-describing token is valid until
    it expires no matter what the server thinks, which is exactly the property
    a sign-out must not have.

    Only the hash is stored, for the same reason passwords are hashed: a leaked
    database should not hand over usable sessions. The raw value is returned to
    the client once, at issue time, and never again.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    # Every token minted by rotating an earlier one keeps its ancestor's family.
    # Presenting an already-rotated token means two clients hold the same
    # lineage, which is theft until proven otherwise — so the family is the
    # unit that gets revoked, not the single token.
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True, default=uuid.uuid4
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
