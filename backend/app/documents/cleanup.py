"""Best-effort upload cleanup after database rows are committed away.

The database and object store cannot commit atomically. Deleting the row first
prefers an invisible orphaned object over a visible row whose bytes were lost.
Cleanup failures are logged and never undo the successful database deletion.
"""

import logging

from app.storage import StorageError, get_storage_provider


logger = logging.getLogger(__name__)


def remove_files(file_paths: list[str]) -> None:
    locators = [locator for locator in file_paths if locator]
    if not locators:
        return
    try:
        get_storage_provider().delete_many(locators)
    except StorageError:
        logger.warning(
            "Could not delete uploaded files",
            exc_info=True,
            extra={"storage_locators": locators},
        )


def remove_directory(*parts: str) -> None:
    """Remove one organization's or one knowledge base's upload prefix."""
    storage = get_storage_provider()
    try:
        prefix = storage.make_locator(*parts)
        storage.delete_prefix(prefix)
    except StorageError:
        logger.warning(
            "Could not delete upload prefix",
            exc_info=True,
            extra={"storage_parts": parts},
        )
