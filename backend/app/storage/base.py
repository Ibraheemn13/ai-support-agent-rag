from collections.abc import Callable, Iterable, Iterator, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Protocol

from fastapi import UploadFile


UPLOAD_CHUNK_SIZE = 1024 * 1024


class StorageError(Exception):
    """The configured storage provider could not complete an operation."""


class StorageObjectNotFoundError(StorageError):
    pass


class StorageLocatorError(StorageError):
    pass


class StorageInvalidUploadError(StorageError):
    pass


class StorageUploadTooLargeError(StorageError):
    pass


@dataclass
class StorageStream:
    chunks: Iterable[bytes]
    content_length: int | None
    close: Callable[[], None]


class StorageProvider(Protocol):
    def make_locator(self, *parts: str) -> str: ...

    async def save_upload(
        self,
        file: UploadFile,
        locator: str,
        *,
        content_type: str,
        max_bytes: int,
    ) -> None: ...

    def exists(self, locator: str) -> bool: ...

    def materialize(self, locator: str) -> AbstractContextManager[Path]: ...

    def open_stream(self, locator: str) -> StorageStream: ...

    def delete_many(self, locators: Sequence[str]) -> None: ...

    def delete_prefix(self, locator_prefix: str) -> None: ...


async def stage_upload(file: UploadFile, max_bytes: int) -> tuple[BinaryIO, int]:
    """Read an upload once, enforcing the same limit for every provider."""
    staged = SpooledTemporaryFile(max_size=min(max_bytes, 8 * 1024 * 1024), mode="w+b")
    total = 0
    try:
        while chunk := await file.read(UPLOAD_CHUNK_SIZE):
            total += len(chunk)
            if total > max_bytes:
                raise StorageUploadTooLargeError
            staged.write(chunk)
        if total == 0:
            raise StorageInvalidUploadError
        staged.seek(0)
        return staged, total
    except Exception:
        staged.close()
        raise


def validate_parts(parts: tuple[str, ...]) -> Iterator[str]:
    """Yield path/key components after rejecting traversal-like values."""
    for part in parts:
        value = str(part).strip()
        if not value or value in {".", ".."} or "/" in value or "\\" in value:
            raise StorageLocatorError("Storage path contains an invalid component")
        yield value
