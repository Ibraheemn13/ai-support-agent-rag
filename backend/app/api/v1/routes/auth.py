from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import enforce_auth_rate_limit, get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
def register(data: UserRegister, db: Annotated[Session, Depends(get_db)]) -> User:
    try:
        return AuthService(db).register(data)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
def login(data: UserLogin, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    try:
        tokens = AuthService(db).login(data)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
def refresh(data: RefreshRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Exchange a refresh token for a new pair.

    Rate limited with the other credential endpoints: this one also takes a
    bearer secret and returns a session, so it is the same class of target as
    login. It takes no access token, because the whole point is to be usable
    once the access token has expired.
    """
    try:
        tokens = AuthService(db).refresh(data.refresh_token)
    except InvalidRefreshTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: RefreshRequest, db: Annotated[Session, Depends(get_db)]) -> None:
    """End the session by revoking the token's whole family.

    Always 204, including for a token that was never valid. Signing out has
    one meaningful outcome — the session is gone — and reporting anything
    else would make this an oracle for which tokens exist.
    """
    AuthService(db).logout(data.refresh_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
