from __future__ import annotations

from dandiapi.api.models.version import Version
from dandiapi.api.services.version.exceptions import DraftVersionPublishingError


def lock_draft_version_for_modification(version: Version) -> Version:
    """
    Lock a draft version, ensuring that it may be modified, and return the locked version.

    This must be called within a transaction, before locking any of the version's assets. The
    publish process locks the draft version before its assets, so acquiring locks in the same
    order here avoids deadlocks. Holding this lock also guarantees that the version can't begin
    publishing until the modification has been committed.
    """
    locked_version = Version.objects.select_for_update().get(id=version.id)
    if locked_version.status == Version.Status.PUBLISHING:
        raise DraftVersionPublishingError

    return locked_version
