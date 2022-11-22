import time

from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.models import Dandiset
from dandiapi.zarr.checksums import (
    ZarrChecksum,
    ZarrChecksumFileUpdater,
    ZarrChecksumListing,
    ZarrChecksums,
    ZarrChecksumUpdater,
    ZarrJSONChecksumSerializer,
)
from dandiapi.zarr.management.commands.ingest_dandiset_zarrs import ingest_dandiset_zarrs
from dandiapi.zarr.management.commands.ingest_zarr_archive import ingest_zarr_archive
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus, ZarrUploadFile


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive_rest(authenticated_api_client, zarr_archive: ZarrArchive, user):
    assign_perm('owner', user, zarr_archive.dandiset)

    # Check status is pending
    resp = authenticated_api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    assert resp.status_code == 200
    assert resp.json()['status'] == ZarrArchiveStatus.PENDING

    # Start ingest
    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/ingest/')
    assert resp.status_code == 204

    # Check status is valid
    resp = authenticated_api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    assert resp.status_code == 200
    assert resp.json()['status'] == ZarrArchiveStatus.COMPLETE


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive_rest_already_active(
    authenticated_api_client, zarr_archive: ZarrArchive, user
):
    assign_perm('owner', user, zarr_archive.dandiset)

    # Emulate ongoing ingest
    zarr_archive.status = ZarrArchiveStatus.INGESTING
    zarr_archive.save()

    # Ensure second ingest fails
    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/ingest/')
    assert resp.status_code == 400
    assert resp.json() == ZarrArchive.INGEST_ERROR_MSG


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive_rest_upload_active(
    authenticated_api_client, zarr_archive: ZarrArchive, zarr_upload_file_factory, user
):
    assign_perm('owner', user, zarr_archive.dandiset)

    # Create active upload
    zarr_upload_file_factory(zarr_archive=zarr_archive, path='foo/bar')
    assert zarr_archive.upload_in_progress

    # Check that ingestion isn't started
    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/ingest/')
    assert resp.status_code == 400
    assert resp.json() == 'Upload in progress. Please cancel or complete this existing upload.'


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive(zarr_upload_file_factory, zarr_archive_factory, faker):
    zarr: ZarrArchive = zarr_archive_factory()

    # Generate > 1000 files, since the page size from S3 is 1000 items
    foo_bar_files: list[ZarrUploadFile] = [
        zarr_upload_file_factory(zarr_archive=zarr, path='foo/bar/a'),
        zarr_upload_file_factory(zarr_archive=zarr, path='foo/bar/b'),
    ]
    foo_baz_files: list[ZarrUploadFile] = [
        zarr_upload_file_factory(zarr_archive=zarr, path=f'foo/baz/{faker.pystr()}')
        for _ in range(1005)
    ]

    # Calculate size and file count
    total_size = sum(f.blob.size for f in (foo_bar_files + foo_baz_files))
    total_file_count = len(foo_bar_files) + len(foo_baz_files)

    # Generate correct listings
    serializer = ZarrJSONChecksumSerializer()
    foo_bar_listing = serializer.generate_listing(files=[f.to_checksum() for f in foo_bar_files])
    foo_baz_listing = serializer.generate_listing(files=[f.to_checksum() for f in foo_baz_files])
    foo_listing = serializer.generate_listing(
        directories=[
            ZarrChecksum(name='bar', digest=foo_bar_listing.digest, size=200),
            ZarrChecksum(name='baz', digest=foo_baz_listing.digest, size=100 * len(foo_baz_files)),
        ]
    )
    root_listing = serializer.generate_listing(
        directories=[ZarrChecksum(name='foo', digest=foo_listing.digest, size=total_size)]
    )

    # Assert checksum files don't already exist
    assert ZarrChecksumFileUpdater(zarr, 'foo/bar').read_checksum_file() is None
    assert ZarrChecksumFileUpdater(zarr, 'foo/baz').read_checksum_file() is None
    assert ZarrChecksumFileUpdater(zarr, 'foo').read_checksum_file() is None
    assert ZarrChecksumFileUpdater(zarr, '').read_checksum_file() is None

    # Assert zarr size and file count is zero
    assert zarr.size == 0
    assert zarr.file_count == 0

    # Compute checksum
    ingest_zarr_archive(str(zarr.zarr_id))

    # Assert files computed correctly
    assert ZarrChecksumFileUpdater(zarr, 'foo/bar').read_checksum_file() == foo_bar_listing
    assert ZarrChecksumFileUpdater(zarr, 'foo/baz').read_checksum_file() == foo_baz_listing
    assert ZarrChecksumFileUpdater(zarr, 'foo').read_checksum_file() == foo_listing
    assert ZarrChecksumFileUpdater(zarr, '').read_checksum_file() == root_listing

    # Assert size and file count matches
    zarr.refresh_from_db()
    assert zarr.size == total_size
    assert zarr.file_count == total_file_count


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive_force(zarr_upload_file_factory, zarr_archive_factory, faker):
    zarr: ZarrArchive = zarr_archive_factory()
    zarr_upload_file_factory(zarr_archive=zarr, path='foo/bar/baz.txt')

    # Perform initial ingest
    ingest_zarr_archive(str(zarr.zarr_id))
    checksum_updater = ZarrChecksumFileUpdater(zarr, '')
    checksum = checksum_updater.read_checksum_file()
    checksum_last_modified = zarr.storage.modified_time(checksum_updater.checksum_file_path)
    assert checksum is not None

    # Last modified time only has second precision, so sleep for 1 second
    time.sleep(1)

    # Perform redundant ingest, ensure checksum hasn't changed
    ingest_zarr_archive(str(zarr.zarr_id))
    assert checksum_updater.read_checksum_file() == checksum
    assert zarr.storage.modified_time(checksum_updater.checksum_file_path) == checksum_last_modified

    # Perform ingest with force flag, assert updated
    ingest_zarr_archive(str(zarr.zarr_id), force=True)
    assert checksum_updater.read_checksum_file() == checksum
    assert zarr.storage.modified_time(checksum_updater.checksum_file_path) != checksum_last_modified


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive_existing(zarr_upload_file_factory, zarr_archive_factory):
    zarr: ZarrArchive = zarr_archive_factory()

    # Add initial files
    a = zarr_upload_file_factory(zarr_archive=zarr, path='foo/a')
    b = zarr_upload_file_factory(zarr_archive=zarr, path='foo/b')
    c = zarr_upload_file_factory(zarr_archive=zarr, path='foo/bar/c')

    # Intentionally generate and save invalid checksum files
    ZarrChecksumUpdater(zarr).update_file_checksums(
        {
            'foo/a': ZarrChecksum(name='a', digest='a', size=100),
            'foo/b': ZarrChecksum(name='b', digest='b', size=100),
            'foo/bar/c': ZarrChecksum(name='c', digest='c', size=100),
        },
    )

    # Generate correct listings
    serializer = ZarrJSONChecksumSerializer()
    foo_bar_listing = serializer.generate_listing(files=[c.to_checksum()])
    foo_listing = serializer.generate_listing(
        files=[
            a.to_checksum(),
            b.to_checksum(),
        ],
        directories=[
            ZarrChecksum(name='bar', digest=foo_bar_listing.digest, size=100),
        ],
    )

    # The root contains an entry for foo
    root_listing = serializer.generate_listing(
        directories=[
            ZarrChecksum(name='foo', digest=foo_listing.digest, size=300),
        ]
    )

    # Assert checksum files exist
    assert ZarrChecksumFileUpdater(zarr, 'foo/bar').read_checksum_file() is not None
    assert ZarrChecksumFileUpdater(zarr, 'foo').read_checksum_file() is not None
    assert ZarrChecksumFileUpdater(zarr, '').read_checksum_file() is not None

    # Compute checksum
    ingest_zarr_archive(str(zarr.zarr_id))

    # Assert files computed correctly
    assert ZarrChecksumFileUpdater(zarr, 'foo/bar').read_checksum_file() == foo_bar_listing
    assert ZarrChecksumFileUpdater(zarr, 'foo').read_checksum_file() == foo_listing
    assert ZarrChecksumFileUpdater(zarr, '').read_checksum_file() == root_listing


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive_empty(zarr_archive_factory):
    zarr: ZarrArchive = zarr_archive_factory()

    # Compute checksum
    ingest_zarr_archive(str(zarr.zarr_id))

    # Assert files computed correctly
    assert ZarrChecksumFileUpdater(zarr, '').read_checksum_file() is None
    assert ZarrJSONChecksumSerializer().generate_listing() == ZarrChecksumListing(
        checksums=ZarrChecksums(directories=[], files=[]),
        digest='481a2f77ab786a0f45aafd5db0971caa-0--0',
        size=zarr.size,
    )


@pytest.mark.django_db(transaction=True)
def test_ingest_zarr_archive_assets(zarr_upload_file_factory, zarr_archive_factory, asset_factory):
    # Create zarr and asset
    zarr: ZarrArchive = zarr_archive_factory()
    zarr_upload_file_factory(zarr_archive=zarr, path='foo/bar/a')
    asset = asset_factory(zarr=zarr, blob=None)

    # Assert asset size, metadata
    assert asset.size == 0
    assert asset.metadata['contentSize'] == 0
    assert asset.metadata['digest']['dandi:dandi-zarr-checksum'] is None

    # Compute checksum
    ingest_zarr_archive(str(zarr.zarr_id))

    # Assert asset size, metadata
    asset.refresh_from_db()
    assert asset.size == 100
    assert asset.metadata['contentSize'] == 100
    assert (
        asset.metadata['digest']['dandi:dandi-zarr-checksum']
        == ZarrChecksumFileUpdater(asset.zarr, '').read_checksum_file().digest
    )


@pytest.mark.django_db(transaction=True)
def test_ingest_dandiset_zarrs(dandiset_factory, zarr_archive_factory, zarr_upload_file_factory):
    dandiset: Dandiset = dandiset_factory()
    for _ in range(10):
        zarr_upload_file_factory(
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
        assert ZarrChecksumFileUpdater(zarr, '').read_checksum_file() is not None
