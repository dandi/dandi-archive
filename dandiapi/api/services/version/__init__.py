from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from dandiapi.api.models.version import Version, VersionModification


def lock_version_for_asset_changes(version: Version) -> None:
    """
    Lock a version for the remainder of the current transaction.

    Anything that adds or removes the assets of a version must call this before it reads or
    modifies any asset path, or the version itself. Whether a path can be used by an asset depends
    on the paths of every other asset of the version, which nothing in the database enforces, so it
    can only be checked while nothing else is able to change them. Those changes also all update
    the version, so without a common lock to wait on first, they could deadlock on it.

    This must be called within a transaction, and it must be the first lock taken in it. Anything
    else that the transaction locks (assets, zarr archives, asset paths) is then only ever locked
    by whichever transaction holds the version, so the order they're locked in doesn't matter.
    """
    # Use `no_key`, as otherwise this would also wait on any transaction that has merely inserted
    # a row referencing this version.
    Version.objects.select_for_update(no_key=True).values_list('id', flat=True).get(id=version.id)


def apply_version_modifications() -> None:
    """Update the `modified` timestamp of every version that has recorded modifications."""
    version_ids = VersionModification.objects.order_by().values_list('version_id', flat=True)
    for version_id in version_ids.distinct():
        with transaction.atomic():
            # Any modification recorded after this is left for the next time this is called. This
            # also discards any modifications of a version that has since been deleted.
            VersionModification.objects.filter(version_id=version_id).delete()
            Version.objects.filter(id=version_id).update(modified=timezone.now())
