from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.management.commands.migrate_zarr_checksums import migrate_zarr_checksums
from dandiapi.api.models import ZarrArchive
from dandiapi.api.tasks.zarr import ingest_zarr_archive


@pytest.mark.django_db()
def test_migration_succeeds(migrator):
    """Ensure that the custom migration code performs correctly."""
    old_state = migrator.apply_initial_migration(
        ('api', '0030_alter_embargoedzarruploadfile_blob_and_more')
    )

    # Get pre-migration models
    ZarrArchive = old_state.apps.get_model('api', 'ZarrArchive')
    Dandiset = old_state.apps.get_model('api', 'Dandiset')

    # Create an old zarr archive with a status of 'COMPLETE'
    # We can't use factories here
    zarr = ZarrArchive.objects.create(
        name='test',
        status='Complete',
        dandiset=Dandiset.objects.create(),
    )

    # Perform migration
    new_state = migrator.apply_tested_migration(
        ('api', '0031_embargoedzarrarchive_checksum_zarrarchive_checksum_and_more')
    )

    # Retrieve same zarr again
    ZarrArchive = new_state.apps.get_model('api', 'ZarrArchive')
    zarr = ZarrArchive.objects.get(id=zarr.id)

    # Assert status was changed to pending, and that checksum is None
    assert zarr.status == 'Pending'
    assert zarr.checksum is None


@pytest.mark.django_db
def test_migrate_zarr_checksums_empty(user, zarr_archive: ZarrArchive):
    assign_perm('owner', user, zarr_archive.dandiset)

    # Assert checksum is None beforehand
    assert zarr_archive.checksum is None
    migrate_zarr_checksums()

    # Assert values have changed
    zarr_archive.refresh_from_db()
    assert zarr_archive.checksum is not None


@pytest.mark.django_db
def test_migrate_zarr_checksums_existing(user, zarr_archive: ZarrArchive, zarr_upload_file_factory):
    assign_perm('owner', user, zarr_archive.dandiset)

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
