import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_refresh_token
from app.models.refresh_token import RefreshToken


PASSWORD = "strongpassword"


def register_and_login(client: TestClient, email: str) -> dict:
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": email},
    ).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return response.json()


def test_login_returns_a_refresh_token_alongside_the_access_token(
    client: TestClient,
) -> None:
    tokens = register_and_login(client, "pair@example.com")

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


def test_refresh_returns_a_working_access_token(client: TestClient) -> None:
    tokens = register_and_login(client, "renew@example.com")

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200

    new_access = refreshed.json()["access_token"]
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "renew@example.com"


def test_refresh_rotates_the_token_so_the_old_one_stops_working(
    client: TestClient,
) -> None:
    """Rotation is what makes a long-lived browser credential defensible."""
    tokens = register_and_login(client, "rotate@example.com")
    original = tokens["refresh_token"]

    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": original}
    ).json()
    assert refreshed["refresh_token"] != original

    replayed = client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert replayed.status_code == 401


def test_replaying_a_rotated_token_kills_the_whole_family(
    client: TestClient,
) -> None:
    """The theft case.

    A replayed token means two holders share one lineage. We cannot tell which
    is the thief, so both lose the session rather than letting the attacker
    keep refreshing behind the real user.
    """
    tokens = register_and_login(client, "stolen@example.com")
    stolen = tokens["refresh_token"]

    # The legitimate client refreshes, rotating `stolen` out.
    current = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": stolen}
    ).json()["refresh_token"]

    # The attacker replays the old copy. It fails...
    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": stolen}).status_code
        == 401
    )

    # ...and the legitimate client's live token is revoked too.
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": current}
        ).status_code
        == 401
    )


def test_logout_ends_the_session(client: TestClient) -> None:
    tokens = register_and_login(client, "signout@example.com")

    assert (
        client.post(
            "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 204
    )
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        ).status_code
        == 401
    )


def test_logout_is_not_an_oracle_for_unknown_tokens(client: TestClient) -> None:
    """A token that was never valid gets the same answer as one that was."""
    response = client.post(
        "/api/v1/auth/logout", json={"refresh_token": "not-a-real-token"}
    )

    assert response.status_code == 204


def test_unknown_refresh_token_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"}
    )

    assert response.status_code == 401


def test_expired_refresh_token_is_rejected(client: TestClient, db: Session) -> None:
    tokens = register_and_login(client, "expired@example.com")

    record = db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(tokens["refresh_token"])
        )
    ).scalar_one()
    record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401


def test_the_raw_token_is_never_stored(client: TestClient, db: Session) -> None:
    """A leaked database must not hand over usable sessions."""
    tokens = register_and_login(client, "hashed@example.com")
    raw = tokens["refresh_token"]

    stored = db.execute(select(RefreshToken.token_hash)).scalars().all()

    assert raw not in stored
    assert hash_refresh_token(raw) in stored


def test_rotation_keeps_one_family_rather_than_starting_a_new_one(
    client: TestClient,
    db: Session,
) -> None:
    tokens = register_and_login(client, "family@example.com")

    client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    families = set(db.execute(select(RefreshToken.family_id)).scalars().all())
    assert len(families) == 1
    assert isinstance(next(iter(families)), uuid.UUID)
