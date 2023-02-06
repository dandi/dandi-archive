import pytest
from zarr_checksum.checksum import EMPTY_CHECKSUM

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

    # Get inital checksum
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
