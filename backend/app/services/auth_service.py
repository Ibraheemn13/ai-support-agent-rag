import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserLogin, UserRegister


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    """The presented refresh token is unknown, expired, or already revoked.

    Deliberately one error for all three. Telling a caller which of them
    applies tells an attacker holding a stolen token whether it was ever real,
    and none of the three has a different remedy: sign in again.
    """


class TokenPair:
    __slots__ = ("access_token", "refresh_token")

    def __init__(self, access_token: str, refresh_token: str) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    """Read a stored timestamp back as an aware UTC datetime.

    Postgres returns `timestamptz` already aware. SQLite, which the test suite
    runs on, has no timezone type and hands back a naive value from the same
    column — so comparing it against an aware "now" raises rather than
    returning a wrong answer. Both are stored in UTC, so attaching the zone
    here is a re-labelling, not a conversion.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def register(self, data: UserRegister) -> User:
        email = str(data.email).strip().lower()
        if self.users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError

        try:
            user = self.users.create(
                email=email,
                full_name=data.full_name,
                password_hash=hash_password(data.password),
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise EmailAlreadyRegisteredError from exc
        self.db.refresh(user)
        return user

    def login(self, data: UserLogin) -> TokenPair:
        user = self.users.get_by_email(str(data.email).strip().lower())
        if user is None or not user.is_active:
            raise InvalidCredentialsError
        if not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError

        refresh_token = self._issue_refresh_token(user_id=user.id)
        self.db.commit()
        return TokenPair(
            access_token=create_access_token(subject=str(user.id)),
            refresh_token=refresh_token,
        )

    def refresh(self, raw_token: str) -> TokenPair:
        """Exchange a refresh token for a new pair, rotating the old one out.

        Rotation is what makes a long-lived credential in the browser
        defensible: a token is single-use, so a stolen one stops working the
        moment the real client refreshes.
        """
        record = self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(raw_token)
            )
        ).scalar_one_or_none()

        if record is None:
            raise InvalidRefreshTokenError

        # A token that was already rotated is being presented a second time.
        # Either it was stolen and replayed, or the legitimate holder is
        # replaying it — and we cannot tell which, so the whole lineage goes.
        # The real user signs in again; the thief's copy is dead too.
        if record.revoked_at is not None:
            self._revoke_family(record.family_id)
            self.db.commit()
            raise InvalidRefreshTokenError

        if _as_aware(record.expires_at) <= _now():
            raise InvalidRefreshTokenError

        user = self.db.get(User, record.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError

        record.revoked_at = _now()
        replacement = self._issue_refresh_token(
            user_id=record.user_id,
            family_id=record.family_id,
        )
        self.db.commit()

        return TokenPair(
            access_token=create_access_token(subject=str(record.user_id)),
            refresh_token=replacement,
        )

    def logout(self, raw_token: str) -> None:
        """Revoke the presented token's whole family.

        Signing out ends the session, not just the one token in hand, so the
        family is the unit. Unknown tokens are ignored rather than reported:
        sign-out is not an oracle for whether a token was ever valid, and a
        caller with a stale token wants the same outcome either way.
        """
        record = self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(raw_token)
            )
        ).scalar_one_or_none()

        if record is not None:
            self._revoke_family(record.family_id)
            self.db.commit()

    def _issue_refresh_token(
        self,
        *,
        user_id: uuid.UUID,
        family_id: uuid.UUID | None = None,
    ) -> str:
        raw_token = generate_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=user_id,
                token_hash=hash_refresh_token(raw_token),
                family_id=family_id or uuid.uuid4(),
                expires_at=_now()
                + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        return raw_token

    def _revoke_family(self, family_id: uuid.UUID) -> None:
        self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=_now())
        )
