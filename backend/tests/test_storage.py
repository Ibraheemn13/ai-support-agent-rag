import asyncio
from io import BytesIO

import pytest
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.storage import (
    StorageInvalidUploadError,
    StorageLocatorError,
    StorageObjectNotFoundError,
    StorageUploadTooLargeError,
)
from app.storage.s3 import S3Storage


class FakeBody(BytesIO):
    def iter_chunks(self, chunk_size: int):
        while chunk := self.read(chunk_size):
            yield chunk


class FakePaginator:
    def __init__(self, client) -> None:
        self.client = client

    def paginate(self, *, Bucket: str, Prefix: str):
        del Bucket
        yield {
            "Contents": [
                {"Key": key}
                for key in sorted(self.client.objects)
                if key.startswith(Prefix)
            ]
        }


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    def upload_fileobj(self, fileobj, bucket, key, ExtraArgs):
        del bucket
        self.objects[key] = fileobj.read()
        self.content_types[key] = ExtraArgs["ContentType"]

    def head_object(self, *, Bucket: str, Key: str):
        del Bucket
        if Key not in self.objects:
            raise missing_object_error()
        return {"ContentLength": len(self.objects[Key])}

    def download_fileobj(self, bucket, key, fileobj):
        del bucket
        if key not in self.objects:
            raise missing_object_error()
        fileobj.write(self.objects[key])

    def get_object(self, *, Bucket: str, Key: str):
        del Bucket
        if Key not in self.objects:
            raise missing_object_error()
        content = self.objects[Key]
        return {"Body": FakeBody(content), "ContentLength": len(content)}

    def delete_objects(self, *, Bucket: str, Delete: dict):
        del Bucket
        for item in Delete["Objects"]:
            self.objects.pop(item["Key"], None)

    def get_paginator(self, operation: str):
        assert operation == "list_objects_v2"
        return FakePaginator(self)


def missing_object_error() -> ClientError:
    return ClientError(
        {
            "Error": {"Code": "NoSuchKey", "Message": "missing"},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        },
        "GetObject",
    )


@pytest.fixture
def s3_storage():
    client = FakeS3Client()
    storage = S3Storage(
        endpoint_url="https://storage.example.com/s3",
        region="us-east-1",
        bucket="documents",
        access_key_id="key",
        secret_access_key="secret",
        prefix="uploads",
        client=client,
    )
    return storage, client


def upload(content: bytes, *, filename: str = "guide.txt") -> UploadFile:
    return UploadFile(file=BytesIO(content), filename=filename)


def test_s3_round_trip_uses_a_private_object_locator(s3_storage):
    storage, client = s3_storage
    locator = storage.make_locator("org-id", "kb-id", "stored.txt")

    asyncio.run(
        storage.save_upload(
            upload(b"support policy"),
            locator,
            content_type="text/plain",
            max_bytes=1024,
        )
    )

    assert locator == "uploads/org-id/kb-id/stored.txt"
    assert storage.exists(locator) is True
    assert client.content_types[locator] == "text/plain"
    with storage.materialize(locator) as path:
        assert path.read_bytes() == b"support policy"
    stream = storage.open_stream(locator)
    assert b"".join(stream.chunks) == b"support policy"
    assert stream.content_length == len(b"support policy")
    stream.close()


def test_s3_prefix_delete_only_removes_that_subtree(s3_storage):
    storage, client = s3_storage
    first = storage.make_locator("org-a", "kb", "one.txt")
    second = storage.make_locator("org-b", "kb", "two.txt")
    client.objects[first] = b"one"
    client.objects[second] = b"two"

    storage.delete_prefix(storage.make_locator("org-a"))

    assert first not in client.objects
    assert second in client.objects


def test_s3_rejects_locators_outside_its_prefix(s3_storage):
    storage, _client = s3_storage

    with pytest.raises(StorageLocatorError):
        storage.open_stream("another-prefix/private.txt")


def test_s3_reports_a_missing_object(s3_storage):
    storage, _client = s3_storage

    with pytest.raises(StorageObjectNotFoundError):
        storage.open_stream("uploads/org/kb/missing.txt")


@pytest.mark.parametrize(
    ("content", "max_bytes", "error"),
    [
        (b"", 10, StorageInvalidUploadError),
        (b"too large", 3, StorageUploadTooLargeError),
    ],
)
def test_upload_validation_is_the_same_for_s3(
    s3_storage,
    content: bytes,
    max_bytes: int,
    error: type[Exception],
):
    storage, _client = s3_storage

    with pytest.raises(error):
        asyncio.run(
            storage.save_upload(
                upload(content),
                "uploads/org/kb/file.txt",
                content_type="text/plain",
                max_bytes=max_bytes,
            )
        )
