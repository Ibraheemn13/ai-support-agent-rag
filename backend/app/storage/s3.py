from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.storage.base import (
    StorageError,
    StorageLocatorError,
    StorageObjectNotFoundError,
    StorageStream,
    stage_upload,
    validate_parts,
)


class S3Storage:
    """Private S3-compatible object storage, including Supabase Storage."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        region: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        prefix: str = "uploads",
        client=None,
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        if not self.prefix:
            raise StorageError("S3_PREFIX cannot be blank")
        self.client = client or boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def make_locator(self, *parts: str) -> str:
        return PurePosixPath(self.prefix, *validate_parts(parts)).as_posix()

    async def save_upload(
        self,
        file: UploadFile,
        locator: str,
        *,
        content_type: str,
        max_bytes: int,
    ) -> None:
        key = self._key(locator)
        staged, _size = await stage_upload(file, max_bytes)
        try:
            await run_in_threadpool(
                self.client.upload_fileobj,
                staged,
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
        except (BotoCoreError, ClientError, OSError) as exc:
            raise StorageError("Could not upload object") from exc
        finally:
            staged.close()

    def exists(self, locator: str) -> bool:
        key = self._key(locator)
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            if self._is_missing(exc):
                return False
            raise StorageError("Could not inspect stored object") from exc
        except BotoCoreError as exc:
            raise StorageError("Could not inspect stored object") from exc

    @contextmanager
    def materialize(self, locator: str):
        key = self._key(locator)
        suffix = Path(key).suffix
        temporary = NamedTemporaryFile(delete=False, suffix=suffix)
        path = Path(temporary.name)
        try:
            with temporary:
                self.client.download_fileobj(self.bucket, key, temporary)
            yield path
        except ClientError as exc:
            if self._is_missing(exc):
                raise StorageObjectNotFoundError(locator) from exc
            raise StorageError("Could not download stored object") from exc
        except BotoCoreError as exc:
            raise StorageError("Could not download stored object") from exc
        finally:
            path.unlink(missing_ok=True)

    def open_stream(self, locator: str) -> StorageStream:
        key = self._key(locator)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if self._is_missing(exc):
                raise StorageObjectNotFoundError(locator) from exc
            raise StorageError("Could not open stored object") from exc
        except BotoCoreError as exc:
            raise StorageError("Could not open stored object") from exc

        body = response["Body"]
        return StorageStream(
            chunks=body.iter_chunks(chunk_size=1024 * 1024),
            content_length=response.get("ContentLength"),
            close=body.close,
        )

    def delete_many(self, locators: Sequence[str]) -> None:
        keys = [self._key(locator) for locator in locators if locator]
        try:
            for offset in range(0, len(keys), 1000):
                batch = keys[offset : offset + 1000]
                if batch:
                    self.client.delete_objects(
                        Bucket=self.bucket,
                        Delete={"Objects": [{"Key": key} for key in batch]},
                    )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Could not delete stored objects") from exc

    def delete_prefix(self, locator_prefix: str) -> None:
        prefix = f"{self._key(locator_prefix).rstrip('/')}/"
        if prefix == f"{self.prefix}/":
            raise StorageError("Refusing to delete the storage root")
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                keys = [item["Key"] for item in page.get("Contents", [])]
                self.delete_many(keys)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Could not delete object prefix") from exc

    def _key(self, locator: str) -> str:
        normalized = PurePosixPath(locator).as_posix().lstrip("/")
        if "\\" in locator or ".." in PurePosixPath(normalized).parts:
            raise StorageLocatorError("Invalid object locator")
        if not normalized.startswith(f"{self.prefix}/"):
            raise StorageLocatorError("Object locator is outside the configured prefix")
        return normalized

    @staticmethod
    def _is_missing(exc: ClientError) -> bool:
        error = exc.response.get("Error", {})
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        return status == 404 or str(error.get("Code")) in {"404", "NoSuchKey", "NotFound"}
