"""CORS configuration: the deploy blocker this closes.

CORS used to register only when `APP_ENV` looked local, so a deployed
frontend was silently blocked by the browser — the request never reached
FastAPI, so nothing in the server logs explained why. These tests are about
the two things that make that mistake hard to repeat: the middleware now
always registers, and a non-local deployment with no origin configured fails
at startup instead of failing silently in someone's browser.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make_settings(
    *,
    app_env: str | None = None,
    frontend_origin: str | None = None,
    jwt_secret_key: str = "a-secure-test-secret",
    **overrides: str,
) -> Settings:
    """Build a `Settings` instance from just the two fields under test.

    `Settings` fields use an alias (`FRONTEND_ORIGIN`, not `frontend_origin`)
    and the model does not enable `populate_by_name`, so constructor kwargs
    have to use the alias — the same as the environment variable name.
    `_env_file=None` keeps a real `backend/.env` on a developer's machine
    from leaking into what should be an isolated test.
    """
    kwargs: dict[str, str] = {"JWT_SECRET_KEY": jwt_secret_key, **overrides}
    if app_env is not None:
        kwargs["APP_ENV"] = app_env
    if frontend_origin is not None:
        kwargs["FRONTEND_ORIGIN"] = frontend_origin
    return Settings(_env_file=None, **kwargs)


def test_a_single_origin_still_works():
    settings = make_settings(frontend_origin="https://app.example.com")

    assert settings.frontend_origins == ["https://app.example.com"]


def test_multiple_origins_are_split_on_commas():
    settings = make_settings(
        frontend_origin="https://app.example.com, https://staging.example.com",
    )

    assert settings.frontend_origins == [
        "https://app.example.com",
        "https://staging.example.com",
    ]


def test_blank_entries_are_dropped():
    """A trailing comma from a copy-pasted env var should not become an
    origin that matches nothing, or worse, an empty-string origin."""
    settings = make_settings(frontend_origin="https://app.example.com,, ,")

    assert settings.frontend_origins == ["https://app.example.com"]


@pytest.mark.parametrize("env", ["local", "development", "dev", "LOCAL", " Dev "])
def test_local_looking_environments_are_recognized(env):
    settings = make_settings(app_env=env, frontend_origin="")

    assert settings.is_local_env is True


@pytest.mark.parametrize("env", ["production", "staging", "render", ""])
def test_non_local_environments_are_not_misidentified(env):
    settings = make_settings(app_env=env, frontend_origin="https://app.example.com")

    assert settings.is_local_env is False


def test_a_local_environment_may_have_no_origin_configured():
    """Local dev falls back to localhost:3000; nothing forces the var to be set."""
    settings = make_settings(app_env="local", frontend_origin="")

    assert settings.frontend_origins == []


def test_a_non_local_environment_with_no_origin_fails_at_startup():
    """The actual bug this closes: silence in production instead of an error.

    A deployed backend with no allowed origin used to start up fine and then
    block the browser on every request, with nothing in the server logs
    pointing at CORS. Refusing to start is the loud version of that failure.
    """
    with pytest.raises(ValidationError, match="FRONTEND_ORIGIN"):
        make_settings(app_env="production", frontend_origin="")


def test_a_non_local_environment_with_only_blank_origins_still_fails():
    with pytest.raises(ValidationError, match="FRONTEND_ORIGIN"):
        make_settings(app_env="production", frontend_origin=" , ,")


def test_a_non_local_environment_with_an_origin_starts_cleanly():
    settings = make_settings(
        app_env="production",
        frontend_origin="https://app.example.com",
    )

    assert settings.frontend_origins == ["https://app.example.com"]


def test_a_non_local_environment_rejects_the_development_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        make_settings(
            app_env="production",
            frontend_origin="https://app.example.com",
            jwt_secret_key="change-me-in-development",
        )


def test_s3_storage_requires_its_credentials():
    with pytest.raises(ValidationError, match="S3 storage requires"):
        make_settings(STORAGE_BACKEND="s3")


def test_complete_s3_storage_configuration_is_accepted():
    configured = make_settings(
        STORAGE_BACKEND="S3",
        S3_ENDPOINT_URL="https://example.storage.local/s3",
        S3_BUCKET="documents",
        S3_ACCESS_KEY_ID="key",
        S3_SECRET_ACCESS_KEY="secret",
        S3_PREFIX="/supportmind/",
    )

    assert configured.storage_backend == "s3"
    assert configured.s3_prefix == "supportmind"
