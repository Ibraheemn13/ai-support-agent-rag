import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.document import Document


CONTENT = b"Refunds are accepted within 30 days of delivery.\n"


def create_user_and_token(client: TestClient, email: str) -> str:
    password = "strongpassword"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": email},
    ).status_code == 201
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    ).json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def upload_document(
    client: TestClient,
    token: str,
    *,
    filename: str = "refund-policy.txt",
    content_type: str = "text/plain",
) -> tuple[str, str]:
    """Return the organization id and the id of one uploaded document."""
    organization = client.post(
        "/api/v1/organizations",
        json={"name": "File Org", "slug": f"org-{uuid.uuid4().hex[:8]}"},
        headers=auth_headers(token),
    ).json()
    knowledge_base = client.post(
        f"/api/v1/organizations/{organization['id']}/knowledge-bases",
        json={"name": "Policies"},
        headers=auth_headers(token),
    ).json()
    document = client.post(
        f"/api/v1/organizations/{organization['id']}/knowledge-bases/"
        f"{knowledge_base['id']}/documents/upload",
        headers=auth_headers(token),
        files={"file": (filename, CONTENT, content_type)},
    ).json()
    return organization["id"], document["id"]


def test_member_can_read_back_the_original_upload(client: TestClient) -> None:
    token = create_user_and_token(client, "reader@example.com")
    organization_id, document_id = upload_document(client, token)

    response = client.get(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/file",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.content == CONTENT
    assert response.headers["content-type"].startswith("text/plain")
    # Inline so the browser renders it rather than downloading it, and named
    # so a download that does happen keeps the name the user recognises.
    assert response.headers["content-disposition"].startswith("inline")
    assert "refund-policy.txt" in response.headers["content-disposition"]


def test_uploaded_bytes_are_never_sniffed_into_another_type(
    client: TestClient,
) -> None:
    """A .txt full of markup must not be able to run as this origin."""
    token = create_user_and_token(client, "sniff@example.com")
    organization_id, document_id = upload_document(client, token)

    response = client.get(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/file",
        headers=auth_headers(token),
    )

    assert response.headers["x-content-type-options"] == "nosniff"


def test_uploaded_bytes_are_not_cached(client: TestClient) -> None:
    """One tenant's file must not be stored by a browser or a shared cache.

    Without this a browser caches heuristically off the etag alone, and goes on
    serving a document whose file has since been deleted.
    """
    token = create_user_and_token(client, "cache@example.com")
    organization_id, document_id = upload_document(client, token)

    response = client.get(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/file",
        headers=auth_headers(token),
    )

    cache_control = response.headers["cache-control"]
    assert "private" in cache_control
    assert "no-store" in cache_control


def test_file_of_another_organization_is_not_readable(client: TestClient) -> None:
    owner = create_user_and_token(client, "owner@example.com")
    organization_id, document_id = upload_document(client, owner)

    outsider = create_user_and_token(client, "outsider@example.com")
    response = client.get(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/file",
        headers=auth_headers(outsider),
    )

    assert response.status_code in {403, 404}


def test_unauthenticated_request_is_rejected(client: TestClient) -> None:
    token = create_user_and_token(client, "anon@example.com")
    organization_id, document_id = upload_document(client, token)

    response = client.get(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/file"
    )

    assert response.status_code == 401


def test_missing_document_is_not_found(client: TestClient) -> None:
    token = create_user_and_token(client, "missing@example.com")
    organization_id, _ = upload_document(client, token)

    response = client.get(
        f"/api/v1/organizations/{organization_id}/documents/{uuid.uuid4()}/file",
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_document_whose_file_has_vanished_reports_gone_not_missing(
    client: TestClient,
    db: Session,
) -> None:
    """The row outliving its bytes is the ephemeral-filesystem case.

    It has to be distinguishable from "no such document", because the document
    is still listed and the reader needs to know which problem they have.
    """
    token = create_user_and_token(client, "vanished@example.com")
    organization_id, document_id = upload_document(client, token)

    document = db.get(Document, uuid.UUID(document_id))
    Path(document.file_path).unlink()

    response = client.get(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/file",
        headers=auth_headers(token),
    )

    assert response.status_code == 410
    assert "no longer stored" in response.json()["detail"]
    # 410 is cacheable by default, and this one must not be: the bytes come
    # back under the same document id after a re-upload, and a pinned 410
    # would go on reporting the file as gone for as long as the cache holds.
    assert response.headers["cache-control"] == "no-store"


def test_stored_path_escaping_the_upload_root_is_refused(
    client: TestClient,
    db: Session,
    tmp_path: Path,
) -> None:
    """Defence in depth against this column ever carrying a path we did not write."""
    token = create_user_and_token(client, "traversal@example.com")
    organization_id, document_id = upload_document(client, token)

    secret = tmp_path / "outside-the-root.txt"
    secret.write_bytes(b"not yours")

    document = db.get(Document, uuid.UUID(document_id))
    document.file_path = str(secret)
    db.commit()

    response = client.get(
        f"/api/v1/organizations/{organization_id}/documents/{document_id}/file",
        headers=auth_headers(token),
    )

    assert response.status_code == 410
    assert b"not yours" not in response.content
