from __future__ import annotations

from dandiapi.api.models.version import Version


def lock_version_for_asset_changes(version: Version) -> None:
    """
    Lock a version for the remainder of the current transaction.

    Anything that adds or removes the assets of a version must call this before it modifies any
    asset path or the version itself. Those changes all write to the same rows (the shared folders
    of the version's asset path tree, and the version), so without a common lock to wait on first,
    concurrent changes acquire those rows in conflicting orders and deadlock.

    This must be called within a transaction. If a zarr archive is also locked in that transaction,
    the version must be locked first, as creating an asset locks its version and then its zarr.
    """
    # Use `no_key`, as otherwise this would also wait on any transaction that has merely inserted
    # a row referencing this version.
    Version.objects.select_for_update(no_key=True).values_list('id', flat=True).get(id=version.id)
