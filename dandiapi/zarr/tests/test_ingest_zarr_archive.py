from django.conf import settings
from guardian.shortcuts import assign_perm
import pytest
from zarr_checksum.checksum import EMPTY_CHECKSUM

from dandiapi.api.models import AssetPath
from dandiapi.api.services.asset import add_asset_to_version
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus
from dandiapi.zarr.tasks import ingest_dandiset_zarrs, ingest_zarr_archive


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive(zarr_archive_factory, zarr_file_factory):
    zarr: ZarrArchive = zarr_archive_factory()
    files = [
        zarr_file_factory(zarr_archive=zarr, path='foo'),
        zarr_file_factory(zarr_archive=zarr, path='bar'),
    ]

    # Calculate total size
    total_size = sum([f.size for f in files])

    # Assert pre-ingest properties
    assert zarr.checksum is None
    assert zarr.size == 0
    assert zarr.file_count == 0
    assert zarr.status == ZarrArchiveStatus.PENDING

    # Compute checksum
    ingest_zarr_archive(str(zarr.zarr_id))

    # Assert checksum properly computed
    zarr.refresh_from_db()
    assert zarr.checksum is not None
    assert zarr.size == total_size
    assert zarr.file_count == 2
    assert zarr.status == ZarrArchiveStatus.COMPLETE


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive_empty(zarr_archive_factory):
    zarr: ZarrArchive = zarr_archive_factory()

    # Compute checksum
    ingest_zarr_archive(str(zarr.zarr_id))

    # Assert correct checksum
    zarr.refresh_from_db()
    assert zarr.checksum == EMPTY_CHECKSUM
    assert zarr.size == 0
    assert zarr.file_count == 0
    assert zarr.status == ZarrArchiveStatus.COMPLETE


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive_force(zarr_archive_factory, zarr_file_factory):
    zarr: ZarrArchive = zarr_archive_factory()

    # Perform initial ingest
    zarr_file_factory(zarr_archive=zarr)
    ingest_zarr_archive(str(zarr.zarr_id))

    # Get initial checksum
    zarr.refresh_from_db()
    first_checksum = zarr.checksum

    # Perform redundant ingest, ensure checksum hasn't changed
    ingest_zarr_archive(str(zarr.zarr_id))
    zarr.refresh_from_db()
    assert zarr.checksum == first_checksum

    # Add file, simulating out of band upload
    zarr_file_factory(zarr_archive=zarr)

    # Perform ingest with force flag, assert updated
    ingest_zarr_archive(str(zarr.zarr_id), force=True)
    zarr.refresh_from_db()
    assert zarr.checksum is not None and zarr.checksum != first_checksum


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive_assets(zarr_archive_factory, zarr_file_factory, asset_factory):
    # Create zarr and asset
    zarr: ZarrArchive = zarr_archive_factory()
    asset = asset_factory(zarr=zarr, blob=None, embargoed_blob=None)

    # Assert asset size, metadata
    assert asset.size == 0
    assert asset.metadata['contentSize'] == 0
    assert asset.metadata['digest']['dandi:dandi-zarr-checksum'] is None

    # Compute checksum
    zarr_file = zarr_file_factory(zarr_archive=zarr)
    ingest_zarr_archive(str(zarr.zarr_id))

    # Assert asset size, metadata
    asset.refresh_from_db()
    zarr.refresh_from_db()
    assert asset.size == zarr_file.size
    assert asset.metadata['contentSize'] == zarr_file.size
    assert asset.metadata['digest']['dandi:dandi-zarr-checksum'] == zarr.checksum


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive_modified(user, draft_version, zarr_archive, zarr_file_factory):
    """Ensure that if the zarr associated to an asset is modified and then ingested, it succeeds."""
    assign_perm('owner', user, draft_version.dandiset)

    # Ensure zarr is ingested with non-zero size
    zarr_file_factory(zarr_archive=zarr_archive, size=100)
    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()

    # Create asset pointing to zarr
    asset = add_asset_to_version(
        user=user,
        version=draft_version,
        zarr_archive=zarr_archive,
        metadata={
            'path': 'sample.zarr',
            'schemaVersion': settings.DANDI_SCHEMA_VERSION,
        },
    )
    assert asset.size == 100
    ap = AssetPath.objects.filter(version=draft_version, asset=asset).first()
    assert ap.aggregate_files == 1
    assert ap.aggregate_size == 100

    # Simulate more data uploaded to the zarr
    zarr_archive.mark_pending()
    zarr_archive.save()
    zarr_archive.refresh_from_db()

    # Ingest zarr
    asset.refresh_from_db()
    ingest_zarr_archive(zarr_archive.zarr_id)


@pytest.mark.django_db(transaction=True)
def test_ingest_dandiset_zarrs(dandiset_factory, zarr_archive_factory, zarr_file_factory):
    dandiset = dandiset_factory()
    for _ in range(10):
        zarr_file_factory(
            path='foo/a',
            zarr_archive=zarr_archive_factory(dandiset=dandiset),
        )

    # Run ingest
    ingest_dandiset_zarrs(str(dandiset.identifier))

    # Assert that zarr archives have been updated
    dandiset.refresh_from_db()
    for zarr in dandiset.zarr_archives.all():
        assert zarr.size != 0
        assert zarr.file_count != 0
        assert zarr.checksum is not None
