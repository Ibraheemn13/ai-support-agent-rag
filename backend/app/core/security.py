import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


password_hasher = PasswordHash.recommended()

# 32 bytes of urandom, URL-safe encoded. Long enough that guessing is not a
# threat model, so the token needs no structure of its own.
REFRESH_TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_hasher.verify(plain_password, password_hash)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload = {"sub": subject, "iat": now, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def generate_refresh_token() -> str:
    """A fresh opaque refresh token. Returned to the client once, never stored."""
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for storage and lookup.

    SHA-256 rather than a password hash, deliberately. A password hash is slow
    on purpose to make guessing a low-entropy human secret expensive; this
    value is 256 bits of urandom, so there is nothing to guess and the cost
    would buy nothing. It would also make lookup impossible: a salted hash
    cannot be searched for, and every refresh needs to find its row by token.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


__all__ = [
    "InvalidTokenError",
    "create_access_token",
    "decode_access_token",
    "generate_refresh_token",
    "hash_password",
    "hash_refresh_token",
    "verify_password",
]
