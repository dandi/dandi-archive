from typing import List

import pytest

from dandiapi.api.management.commands.compute_zarr_checksum import compute_zarr_checksum
from dandiapi.api.models.zarr import ZarrArchive, ZarrUploadFile
from dandiapi.api.zarr_checksums import (
    ZarrChecksum,
    ZarrChecksumFileUpdater,
    ZarrChecksumListing,
    ZarrChecksums,
    ZarrChecksumUpdater,
    ZarrJSONChecksumSerializer,
)


@pytest.mark.django_db
def test_compute_zarr_checksum(zarr_upload_file_factory, zarr_archive_factory, faker):
    zarr: ZarrArchive = zarr_archive_factory()

    # Generate > 1000 files, since the page size from S3 is 1000 items
    foo_bar_files: List[ZarrUploadFile] = [
        zarr_upload_file_factory(zarr_archive=zarr, path='foo/bar/a'),
        zarr_upload_file_factory(zarr_archive=zarr, path='foo/bar/b'),
    ]
    foo_baz_files: List[ZarrUploadFile] = [
        zarr_upload_file_factory(zarr_archive=zarr, path=f'foo/baz/{faker.pystr()}')
        for _ in range(1005)
    ]

    # Calculate size and file count
    total_size = sum([f.blob.size for f in (foo_bar_files + foo_baz_files)])
    total_file_count = len(foo_bar_files) + len(foo_baz_files)

    # Generate correct listings
    serializer = ZarrJSONChecksumSerializer()
    foo_bar_listing = serializer.generate_listing(files=[f.to_checksum() for f in foo_bar_files])
    foo_baz_listing = serializer.generate_listing(files=[f.to_checksum() for f in foo_baz_files])
    foo_listing = serializer.generate_listing(
        directories=[
            ZarrChecksum(path='foo/bar', md5=foo_bar_listing.md5),
            ZarrChecksum(path='foo/baz', md5=foo_baz_listing.md5),
        ]
    )
    root_listing = serializer.generate_listing(
        directories=[ZarrChecksum(path='foo', md5=foo_listing.md5)]
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
    compute_zarr_checksum(str(zarr.id))

    # Assert files computed correctly
    assert ZarrChecksumFileUpdater(zarr, 'foo/bar').read_checksum_file() == foo_bar_listing
    assert ZarrChecksumFileUpdater(zarr, 'foo/baz').read_checksum_file() == foo_baz_listing
    assert ZarrChecksumFileUpdater(zarr, 'foo').read_checksum_file() == foo_listing
    assert ZarrChecksumFileUpdater(zarr, '').read_checksum_file() == root_listing

    # Assert size and file count matches
    zarr.refresh_from_db()
    assert zarr.size == total_size
    assert zarr.file_count == total_file_count


@pytest.mark.django_db
def test_compute_zarr_checksum_existing(zarr_upload_file_factory, zarr_archive_factory):
    zarr: ZarrArchive = zarr_archive_factory()

    # Add initial files
    a = zarr_upload_file_factory(zarr_archive=zarr, path='foo/a')
    b = zarr_upload_file_factory(zarr_archive=zarr, path='foo/b')
    c = zarr_upload_file_factory(zarr_archive=zarr, path='foo/bar/c')

    # Intentionally generate and save invalid checksum files
    ZarrChecksumUpdater(zarr).update_file_checksums(
        [
            ZarrChecksum(path='foo/a', md5='a'),
            ZarrChecksum(path='foo/b', md5='b'),
            ZarrChecksum(path='foo/bar/c', md5='c'),
        ],
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
            ZarrChecksum(path='foo/bar', md5=foo_bar_listing.md5),
        ],
    )

    # The root contains an entry for foo
    root_listing = serializer.generate_listing(
        directories=[
            ZarrChecksum(path='foo', md5=foo_listing.md5),
        ]
    )

    # Assert checksum files exist
    assert ZarrChecksumFileUpdater(zarr, 'foo/bar').read_checksum_file() is not None
    assert ZarrChecksumFileUpdater(zarr, 'foo').read_checksum_file() is not None
    assert ZarrChecksumFileUpdater(zarr, '').read_checksum_file() is not None

    # Compute checksum
    compute_zarr_checksum(str(zarr.id))

    # Assert files computed correctly
    assert ZarrChecksumFileUpdater(zarr, 'foo/bar').read_checksum_file() == foo_bar_listing
    assert ZarrChecksumFileUpdater(zarr, 'foo').read_checksum_file() == foo_listing
    assert ZarrChecksumFileUpdater(zarr, '').read_checksum_file() == root_listing


@pytest.mark.django_db
def test_compute_zarr_checksum_empty(zarr_archive_factory):
    zarr: ZarrArchive = zarr_archive_factory()

    # Compute checksum
    compute_zarr_checksum(str(zarr.id))

    # Assert files computed correctly
    assert ZarrChecksumFileUpdater(zarr, '').read_checksum_file() is None
    assert ZarrJSONChecksumSerializer().generate_listing() == ZarrChecksumListing(
        checksums=ZarrChecksums(directories=[], files=[]),
        md5='481a2f77ab786a0f45aafd5db0971caa',
    )
