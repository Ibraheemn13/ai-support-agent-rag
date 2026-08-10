import shutil
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path

from fastapi import UploadFile

from app.core.storage import resolve_storage_path
from app.storage.base import (
    StorageError,
    StorageLocatorError,
    StorageObjectNotFoundError,
    StorageStream,
    stage_upload,
    validate_parts,
)


class LocalStorage:
    def __init__(self, root: str | Path) -> None:
        self.configured_root = Path(root)
        self.root = resolve_storage_path(self.configured_root)

    def make_locator(self, *parts: str) -> str:
        locator = self.configured_root.joinpath(*validate_parts(parts))
        self._resolve(locator)
        return locator.as_posix()

    async def save_upload(
        self,
        file: UploadFile,
        locator: str,
        *,
        content_type: str,
        max_bytes: int,
    ) -> None:
        del content_type
        destination = self._resolve(locator)
        staged, _size = await stage_upload(file, max_bytes)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as output:
                shutil.copyfileobj(staged, output)
        except OSError as exc:
            destination.unlink(missing_ok=True)
            raise StorageError("Could not write uploaded file") from exc
        finally:
            staged.close()

    def exists(self, locator: str) -> bool:
        return self._resolve(locator).is_file()

    @contextmanager
    def materialize(self, locator: str):
        path = self._resolve(locator)
        if not path.is_file():
            raise StorageObjectNotFoundError(locator)
        yield path

    def open_stream(self, locator: str) -> StorageStream:
        path = self._resolve(locator)
        try:
            handle = path.open("rb")
        except FileNotFoundError as exc:
            raise StorageObjectNotFoundError(locator) from exc
        except OSError as exc:
            raise StorageError("Could not open stored file") from exc

        def chunks():
            try:
                while chunk := handle.read(1024 * 1024):
                    yield chunk
            finally:
                handle.close()

        return StorageStream(
            chunks=chunks(),
            content_length=path.stat().st_size,
            close=handle.close,
        )

    def delete_many(self, locators: Sequence[str]) -> None:
        for locator in locators:
            try:
                self._resolve(locator).unlink(missing_ok=True)
            except OSError as exc:
                raise StorageError("Could not delete stored file") from exc

    def delete_prefix(self, locator_prefix: str) -> None:
        target = self._resolve(locator_prefix)
        if target == self.root:
            raise StorageError("Refusing to delete the storage root")
        try:
            shutil.rmtree(target, ignore_errors=True)
        except OSError as exc:
            raise StorageError("Could not delete storage directory") from exc

    def _resolve(self, locator: str | Path) -> Path:
        path = resolve_storage_path(locator)
        if not path.is_relative_to(self.root):
            raise StorageLocatorError("Storage locator is outside the upload directory")
        return path
