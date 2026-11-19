from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading
import time
from typing import TYPE_CHECKING

from dandischema.consts import DANDI_SCHEMA_VERSION
from django.db import connection
import pytest

from dandiapi.api import asset_paths
from dandiapi.api.models.asset_paths import AssetPath
from dandiapi.api.services import asset as asset_service
from dandiapi.api.services.asset import (
    add_asset_to_version,
    bulk_remove_assets_from_version,
    change_asset,
    remove_asset_from_version,
)
from dandiapi.api.services.asset.exceptions import AssetNotInVersionError, AssetPathConflictError
from dandiapi.api.tests.factories import (
    AssetBlobFactory,
    DraftAssetFactory,
    DraftVersionFactory,
    UserFactory,
)
from dandiapi.zarr.models import ZarrArchiveStatus
from dandiapi.zarr.tasks import ingest_zarr_archive
from dandiapi.zarr.tests.factories import ZarrArchiveFactory

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from django.contrib.auth.models import User
    from pytest_mock import MockerFixture

    from dandiapi.api.models import Asset, Version

# How long to wait on another thread before giving up. Nothing should ever take this long.
TIMEOUT = 10


class _Pause:
    """A point at which a thread stops, until it's resumed by the test."""

    def __init__(self) -> None:
        self.reached = threading.Event()
        self._resumed = threading.Event()

    def wait_here(self) -> None:
        self.reached.set()
        self._resumed.wait(timeout=TIMEOUT)

    def resume(self) -> None:
        self._resumed.set()


def _pause_after(mocker: MockerFixture, module: ModuleType, function_name: str, path: str):
    """Pause any thread that calls the given function for an asset at `path`, once it returns."""
    pause = _Pause()
    original = getattr(module, function_name)

    def call_then_pause(*args, **kwargs):
        result = original(*args, **kwargs)

        asset: Asset = kwargs['asset'] if 'asset' in kwargs else args[0]
        if asset.path == path:
            pause.wait_here()

        return result

    mocker.patch.object(module, function_name, side_effect=call_then_pause)
    return pause


def _in_thread(func: Callable[[], object]) -> Callable[[], None]:
    """Wrap a function that is run in another thread, to close the database connection it opens."""

    def wrapper():
        try:
            func()
        finally:
            connection.close()

    return wrapper


def _transaction_is_blocked() -> bool:
    """Return whether any transaction in the test database is waiting on a lock."""
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT count(*) FROM pg_stat_activity '
            "WHERE datname = current_database() AND wait_event_type = 'Lock'"
        )
        return cursor.fetchone()[0] > 0


def _wait_until(condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.01)

    pytest.fail('Timed out waiting on another thread')


@pytest.fixture
def version_with_assets() -> tuple[User, Version, Asset, Asset]:
    """Create a draft version owned by a new user, containing `a/moved.nwb` and `b/existing.nwb`."""
    user = UserFactory.create()
    version = DraftVersionFactory.create(dandiset__owners=[user])
    moved = DraftAssetFactory.create(path='a/moved.nwb')
    existing = DraftAssetFactory.create(path='b/existing.nwb')
    for asset in [moved, existing]:
        version.assets.add(asset)
        asset_paths.add_asset_paths(asset, version)

    return user, version, moved, existing


def _move_asset(user: User, version: Version, moved: Asset) -> Callable[[], object]:
    """Return a change that moves `a/moved.nwb` into the `b` folder."""
    return lambda: change_asset(
        user=user,
        asset=moved,
        version=version,
        new_asset_blob=moved.blob,
        new_metadata={**moved.metadata, 'path': 'b/moved.nwb'},
    )


# Each of the following is a change to the assets of a version, which modifies the `b` folder
# that already contains `existing`. They perform any required setup, and return the change itself.


def _create_asset(
    user: User, version: Version, existing: Asset, path: str = 'b/new.nwb'
) -> Callable[[], object]:
    asset_blob = AssetBlobFactory.create()
    return lambda: add_asset_to_version(
        user=user,
        version=version,
        asset_blob=asset_blob,
        metadata={'path': path, 'schemaVersion': DANDI_SCHEMA_VERSION},
    )


def _remove_asset(user: User, version: Version, existing: Asset) -> Callable[[], object]:
    return lambda: remove_asset_from_version(user=user, asset=existing, version=version)


def _bulk_remove_assets(user: User, version: Version, existing: Asset) -> Callable[[], object]:
    return lambda: bulk_remove_assets_from_version(
        user=user, version=version, asset_ids=[existing.asset_id]
    )


def _ingest_zarr(user: User, version: Version, existing: Asset) -> Callable[[], object]:
    zarr_archive = ZarrArchiveFactory.create(dandiset=version.dandiset)
    add_asset_to_version(
        user=user,
        version=version,
        zarr_archive=zarr_archive,
        metadata={'path': 'b/new.zarr', 'schemaVersion': DANDI_SCHEMA_VERSION},
    )
    zarr_archive.status = ZarrArchiveStatus.UPLOADED
    zarr_archive.save()

    return lambda: ingest_zarr_archive(str(zarr_archive.zarr_id))


@pytest.mark.parametrize(
    ('prepare_change', 'expected_files'),
    [
        (_create_asset, 3),
        (_remove_asset, 1),
        (_bulk_remove_assets, 1),
        (_ingest_zarr, 3),
    ],
    ids=['create', 'remove', 'bulk-remove', 'ingest-zarr'],
)
@pytest.mark.django_db(transaction=True)
def test_asset_changes_during_asset_move_do_not_deadlock(
    prepare_change, expected_files, version_with_assets, mocker
):
    """
    Test that the assets of a version can be changed while one of them is being moved.

    Moving an asset removes it from its old folder, updates the version, and then adds it to its
    new folder. Any other change to that new folder first modifies the folder and then updates the
    version. If the version isn't locked before either of them starts, the move ends up holding the
    version while waiting on the folder, and the other change the opposite, which is a deadlock.
    """
    user, version, moved, existing = version_with_assets
    move_asset = _move_asset(user, version, moved)
    other_change = prepare_change(user, version, existing)

    # Pause the move once it has removed the asset from its old folder, which is the point at which
    # it has updated the version, but hasn't yet touched the new folder.
    move_pause = _pause_after(
        mocker, asset_service, '_remove_asset_from_version', path='a/moved.nwb'
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        try:
            move = executor.submit(_in_thread(move_asset))
            assert move_pause.reached.wait(timeout=TIMEOUT)

            # Start the other change, and only let the move continue once the other change has
            # gotten as far as it can without the move finishing.
            other = executor.submit(_in_thread(other_change))
            _wait_until(_transaction_is_blocked)
        finally:
            move_pause.resume()

        # If these deadlocked, one of them raises here, as it was aborted to resolve the deadlock
        move.result(timeout=TIMEOUT)
        other.result(timeout=TIMEOUT)

    # Both changes were applied, leaving the asset paths in a consistent state
    assert version.assets.filter(path='b/moved.nwb').exists()
    assert not AssetPath.objects.filter(version=version, path='a').exists()
    assert AssetPath.objects.get(version=version, path='b').aggregate_files == expected_files


@pytest.mark.parametrize(
    ('module', 'function_name', 'path'),
    [
        # The move has updated the version, and next inserts the new folder
        (asset_service, '_remove_asset_from_version', 'a/moved.nwb'),
        # The move has also inserted the new folder, and next updates its size and file count
        (asset_paths, 'insert_asset_paths', 'b/moved.nwb'),
    ],
    ids=['folder-insert', 'folder-size-update'],
)
@pytest.mark.django_db(transaction=True)
def test_asset_move_blocked_by_asset_create_does_not_deadlock(
    module, function_name, path, version_with_assets, mocker
):
    """
    Test that an asset can be moved into a folder while another asset is being created in it.

    This is the same deadlock as in the test above, but here the create is first to modify the
    folder, so it's the move that is made to wait on the folder, at each of the two points where it
    writes to it. Then the create waits on the version, which the move has already updated.
    """
    user, version, moved, existing = version_with_assets
    move_asset = _move_asset(user, version, moved)
    create_asset = _create_asset(user, version, existing)

    move_pause = _pause_after(mocker, module, function_name, path=path)

    # Pause the create once it has modified the folder, which is right before it updates the version
    create_pause = _pause_after(mocker, asset_service, 'add_asset_paths', path='b/new.nwb')

    with ThreadPoolExecutor(max_workers=2) as executor:
        try:
            move = executor.submit(_in_thread(move_asset))
            assert move_pause.reached.wait(timeout=TIMEOUT)

            # Either the create modifies the folder and pauses, or it's stopped earlier by the move
            create = executor.submit(_in_thread(create_asset))
            _wait_until(lambda: create_pause.reached.is_set() or _transaction_is_blocked())

            # Let the move run until it's waiting on the create, unless the create is the one
            # waiting, in which case there's nothing stopping the move from finishing.
            move_pause.resume()
            _wait_until(lambda: move.done() or _transaction_is_blocked())
        finally:
            move_pause.resume()
            create_pause.resume()

        # If these deadlocked, one of them raises here, as it was aborted to resolve the deadlock
        move.result(timeout=TIMEOUT)
        create.result(timeout=TIMEOUT)

    # Both changes were applied, with the size and file count of the folder accounting for both
    new = version.assets.get(path='b/new.nwb')
    folder = AssetPath.objects.get(version=version, path='b')
    assert folder.aggregate_files == 3
    assert folder.aggregate_size == existing.size + moved.size + new.size
    assert not AssetPath.objects.filter(version=version, path='a').exists()


@pytest.mark.parametrize(
    ('first_path', 'second_path'),
    [
        ('c/data', 'c/data/new.nwb'),
        ('c/data/new.nwb', 'c/data'),
    ],
    ids=['file-then-folder', 'folder-then-file'],
)
@pytest.mark.django_db(transaction=True)
def test_asset_create_conflicting_with_concurrent_asset_create(
    first_path, second_path, version_with_assets, mocker
):
    """Test that a path can't be used as both a file and a folder by concurrently created assets."""
    user, version, _, existing = version_with_assets
    create_first = _create_asset(user, version, existing, path=first_path)
    create_second = _create_asset(user, version, existing, path=second_path)

    # Pause the first create once it has added its path, which the second hasn't been able to see
    first_pause = _pause_after(mocker, asset_service, 'add_asset_paths', path=first_path)

    with ThreadPoolExecutor(max_workers=2) as executor:
        try:
            first = executor.submit(_in_thread(create_first))
            assert first_pause.reached.wait(timeout=TIMEOUT)

            second = executor.submit(_in_thread(create_second))
            _wait_until(_transaction_is_blocked)
        finally:
            first_pause.resume()

        first.result(timeout=TIMEOUT)
        with pytest.raises(AssetPathConflictError):
            second.result(timeout=TIMEOUT)

    assert version.assets.filter(path=first_path).exists()
    assert not version.assets.filter(path=second_path).exists()


@pytest.mark.django_db(transaction=True)
def test_asset_update_of_concurrently_removed_asset(version_with_assets, mocker):
    """Test that an asset can't be updated once a concurrent request has removed it."""
    user, version, _, existing = version_with_assets
    remove_asset = _remove_asset(user, version, existing)

    def update_asset():
        change_asset(
            user=user,
            asset=existing,
            version=version,
            new_asset_blob=existing.blob,
            new_metadata={**existing.metadata, 'path': 'b/renamed.nwb'},
        )

    # Pause the removal once it has been performed, but before it's visible to the update
    remove_pause = _pause_after(
        mocker, asset_service, '_remove_asset_from_version', path='b/existing.nwb'
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        try:
            removal = executor.submit(_in_thread(remove_asset))
            assert remove_pause.reached.wait(timeout=TIMEOUT)

            update = executor.submit(_in_thread(update_asset))
            _wait_until(_transaction_is_blocked)
        finally:
            remove_pause.resume()

        removal.result(timeout=TIMEOUT)
        with pytest.raises(AssetNotInVersionError):
            update.result(timeout=TIMEOUT)

    assert not version.assets.filter(path__startswith='b/').exists()
