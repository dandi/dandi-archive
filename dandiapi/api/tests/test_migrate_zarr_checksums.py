import pytest

from dandiapi.api.management.commands.migrate_zarr_checksums import migrate_zarr_checksums
from dandiapi.api.models import ZarrArchive
from dandiapi.api.tasks.zarr import ingest_zarr_archive


@pytest.mark.django_db
def test_migrate_zarr_checksums(zarr_archive_factory, zarr_upload_file_factory):
    zarr_archive: ZarrArchive = zarr_archive_factory()

    # Create files
    for _ in range(10):
        zarr_upload_file_factory(zarr_archive=zarr_archive)

    # We need to complete the upload before the checksum files to be written.
    zarr_archive.complete_upload()

    # Ingest, so checksum files are written
    ingest_zarr_archive(zarr_archive.zarr_id)

    # Intentionally update checksum and status fields, to simulate the migration
    zarr_archive.checksum = None
    zarr_archive.status = ZarrArchive.Status.PENDING
    zarr_archive.save()

    # Migrate checksums
    migrate_zarr_checksums()

    # Assert values have changed
    zarr_archive.refresh_from_db()
    assert zarr_archive.checksum is not None
    assert zarr_archive.status == ZarrArchive.Status.COMPLETE


@pytest.mark.django_db
def test_migrate_zarr_checksums_uningested(zarr_archive_factory, zarr_upload_file_factory):
    zarr_archive: ZarrArchive = zarr_archive_factory()

    # Create files
    for _ in range(10):
        zarr_upload_file_factory(zarr_archive=zarr_archive)

    # We need to complete the upload before the checksum files to be written.
    zarr_archive.complete_upload()

    # Intentionally don't run ingestion
    # Intentionally update checksum and status fields, to simulate the migration
    zarr_archive.checksum = None
    zarr_archive.status = ZarrArchive.Status.PENDING
    zarr_archive.save()

    # Migrate checksums
    migrate_zarr_checksums()

    # Assert values have changed
    zarr_archive.refresh_from_db()
    assert zarr_archive.checksum is None
    assert zarr_archive.status == ZarrArchive.Status.PENDING
