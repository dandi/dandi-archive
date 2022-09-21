from __future__ import annotations

from pathlib import Path

import pytest

from dandiapi.zarr.checksums import (
    ZarrChecksum,
    ZarrChecksumFileUpdater,
    ZarrChecksumListing,
    ZarrChecksumModification,
    ZarrChecksumModificationQueue,
    ZarrChecksums,
    ZarrChecksumUpdater,
    ZarrJSONChecksumSerializer,
)
from dandiapi.zarr.models import ZarrArchive, ZarrUploadFile


def test_zarr_checksum_sort_order():
    # The a < b in the name should take precedence over z > y in the md5
    a = ZarrChecksum(name='a', digest='z', size=3)
    b = ZarrChecksum(name='b', digest='y', size=4)
    assert sorted([b, a]) == [a, b]


# ZarrJSONChecksumSerializer tests


@pytest.mark.parametrize(
    'file_checksums,directory_checksums,checksum',
    [
        ([], [], '481a2f77ab786a0f45aafd5db0971caa-0--0'),
        (
            [ZarrChecksum(name='bar', digest='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', size=1)],
            [],
            'f21b9b4bf53d7ce1167bcfae76371e59-1--1',
        ),
        (
            [],
            [ZarrChecksum(name='foo/bar', digest='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-1--1', size=1)],
            '413274f13134fa8a83a7f94e96c5a3c9-1--1',
        ),
        (
            [
                ZarrChecksum(name='bar', digest='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', size=1),
                ZarrChecksum(name='baz', digest='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', size=2),
            ],
            [],
            '4e67de4393d14c1e9c472438f0f1f8b1-2--3',
        ),
        (
            [],
            [
                ZarrChecksum(name='bar', digest='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-1--1', size=1),
                ZarrChecksum(name='baz', digest='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-1--2', size=2),
            ],
            '859ca1926affe9c7d0424030f26fbd89-2--3',
        ),
        (
            [ZarrChecksum(name='baz', digest='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', size=1)],
            [ZarrChecksum(name='bar', digest='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-1--2', size=2)],
            '3cb139f47d3a3580388f41956c15f55e-2--3',
        ),
    ],
)
def test_zarr_checksum_serializer_aggregate_checksum(file_checksums, directory_checksums, checksum):
    serializer = ZarrJSONChecksumSerializer()
    assert (
        serializer.aggregate_digest(
            ZarrChecksums(files=file_checksums, directories=directory_checksums)
        )
        == checksum
    )


def test_zarr_checksum_serializer_generate_listing():
    serializer = ZarrJSONChecksumSerializer()
    checksums = ZarrChecksums(
        files=[ZarrChecksum(name='bar', digest='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', size=1)],
        directories=[
            ZarrChecksum(name='baz', digest='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-1--2', size=2)
        ],
    )
    assert serializer.generate_listing(checksums) == ZarrChecksumListing(
        checksums=checksums,
        digest='baf791d7bac84947c14739b1684ec5ab-2--3',
        size=3,
    )


def test_zarr_serialize():
    serializer = ZarrJSONChecksumSerializer()
    assert (
        serializer.serialize(
            ZarrChecksumListing(
                checksums=ZarrChecksums(
                    files=[ZarrChecksum(name='foo', digest='a', size=1)],
                    directories=[ZarrChecksum(name='bar', digest='b', size=2)],
                ),
                digest='c',
                size=3,
            )
        )
        == '{"checksums":{"directories":[{"digest":"b","name":"bar","size":2}],"files":[{"digest":"a","name":"foo","size":1}]},"digest":"c","size":3}'  # noqa: E501
    )


def test_zarr_deserialize():
    serializer = ZarrJSONChecksumSerializer()
    assert serializer.deserialize(
        '{"checksums":{"directories":[{"digest":"b","name":"bar/foo","size":2}],"files":[{"digest":"a","name":"foo/bar","size":1}]},"digest":"c", "size":3}'  # noqa: E501
    ) == ZarrChecksumListing(
        checksums=ZarrChecksums(
            files=[ZarrChecksum(name='foo/bar', digest='a', size=1)],
            directories=[ZarrChecksum(name='bar/foo', digest='b', size=2)],
        ),
        digest='c',
        size=3,
    )


# ZarrChecksumFileUpdater tests


@pytest.mark.django_db
def test_zarr_checksum_file_updater_checksum_file_path(
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    upload: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    upload_parent_path = str(Path(upload.path).parent)
    assert (
        ZarrChecksumFileUpdater(zarr_archive, upload_parent_path).checksum_file_path
        == f'test-prefix/test-zarr-checksums/{zarr_archive.zarr_id}/{upload_parent_path}/.checksum'
    )

    # The root path is represented as Path('.')
    assert (
        ZarrChecksumFileUpdater(zarr_archive, Path('.')).checksum_file_path
        == f'test-prefix/test-zarr-checksums/{zarr_archive.zarr_id}/.checksum'
    )
    assert (
        ZarrChecksumFileUpdater(zarr_archive, Path('foo').parent).checksum_file_path
        == f'test-prefix/test-zarr-checksums/{zarr_archive.zarr_id}/.checksum'
    )


@pytest.mark.django_db
def test_zarr_checksum_file_updater_write_checksum_file(
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    upload: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    upload_parent_path = str(Path(upload.path).parent)
    listing = ZarrChecksumListing(
        checksums=ZarrChecksums(
            files=[
                upload.to_checksum(),
            ]
        ),
        digest='b',
        size=1,
    )

    updater = ZarrChecksumFileUpdater(zarr_archive, upload_parent_path)
    updater.write_checksum_file(listing)

    storage = upload.blob.storage
    assert storage.exists(updater.checksum_file_path)
    with storage.open(updater.checksum_file_path) as f:
        contents = f.read()
        assert ZarrJSONChecksumSerializer().deserialize(contents) == listing

    # Now that the checksum file has been written, verify that it can be updated
    second_upload = zarr_upload_file_factory(zarr_archive=zarr_archive, path=f'{upload.path}2')
    listing.checksums.files.append(second_upload.to_checksum())

    updater.write_checksum_file(listing)

    assert storage.exists(updater.checksum_file_path)
    with storage.open(updater.checksum_file_path) as f:
        contents = f.read()
        assert ZarrJSONChecksumSerializer().deserialize(contents) == listing


@pytest.mark.django_db
def test_zarr_checksum_file_updater_read_checksum_file(
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    upload: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    upload_parent_path = str(Path(upload.path).parent)
    listing = ZarrChecksumListing(
        checksums=ZarrChecksums(files=[upload.to_checksum()]), digest='b', size=1
    )

    updater = ZarrChecksumFileUpdater(zarr_archive, upload_parent_path)
    updater.write_checksum_file(listing)
    assert updater.read_checksum_file() == listing


@pytest.mark.django_db
def test_zarr_checksum_file_updater_delete_checksum_file(
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    upload: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    upload_parent_path = str(Path(upload.path).parent)

    updater = ZarrChecksumFileUpdater(zarr_archive, upload_parent_path)
    updater.delete_checksum_file()
    assert updater.read_checksum_file() is None
    assert not upload.blob.storage.exists(updater.checksum_file_path)


@pytest.mark.django_db
def test_zarr_checksum_file_updater_context_manager(
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    upload: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    upload_parent_path = str(Path(upload.path).parent)
    serializer = ZarrJSONChecksumSerializer()
    checksums = [upload.to_checksum()]
    listing = serializer.generate_listing(files=checksums)

    updater = ZarrChecksumFileUpdater(zarr_archive, upload_parent_path)
    updater.write_checksum_file(listing)

    with ZarrChecksumFileUpdater(zarr_archive, upload_parent_path) as updater:
        # Initializing the context manager loads the checksum file
        assert updater.checksum_listing == listing

        # Add two new checksums to the updater
        a = ZarrChecksum(name='bar', digest='a', size=1)
        b = ZarrChecksum(name='baz', digest='b', size=2)
        # Duplicate checksums should be removed
        updater.add_file_checksums(sorted([upload.to_checksum(), a, a, b, b]))
        # The updater's internal state should be updated
        assert updater.checksum_listing == serializer.generate_listing(
            files=sorted(checksums + [a, b])
        )

        # Remove the A checksum from the updater
        # The md5 should not need to match
        updater.remove_checksums([a.name])
        assert updater.checksum_listing == serializer.generate_listing(
            files=sorted(checksums + [b])
        )

        # The file should not yet be updated with our changes
        assert updater.read_checksum_file() == serializer.generate_listing(files=sorted(checksums))

    # Exiting the context should write the checksum file
    assert updater.read_checksum_file() == serializer.generate_listing(
        files=sorted(checksums + [b])
    )


# ZarrChecksumModificationQueue tests


foo = ZarrChecksum(name='foo', digest='a', size=2)
bar = ZarrChecksum(name='bar', digest='b', size=1)
foo_bar = ZarrChecksum(name='bar', digest='c', size=2)
foo_bar_baz = ZarrChecksum(name='baz', digest='d', size=2)
# This is a convenient way to get the correct parent directory for a given checksum
parent_directory_map = {
    foo.digest: Path('.'),
    bar.digest: Path('.'),
    foo_bar.digest: Path('foo'),
    foo_bar_baz.digest: Path('foo/bar'),
}


@pytest.mark.parametrize(
    'file_updates,directory_updates,removals,modifications',
    [
        (
            [foo],
            [],
            [],
            [ZarrChecksumModification(Path('.'), files_to_update=[foo])],
        ),
        (
            [],
            [foo],
            [],
            [ZarrChecksumModification(Path('.'), directories_to_update=[foo])],
        ),
        (
            [],
            [],
            ['foo'],
            [ZarrChecksumModification(Path('.'), paths_to_remove=['foo'])],
        ),
        (
            [foo, bar],
            [],
            [],
            [ZarrChecksumModification(Path('.'), files_to_update=[foo, bar])],
        ),
        (
            [foo_bar],
            [foo],
            [],
            [
                ZarrChecksumModification(Path('foo'), files_to_update=[foo_bar]),
                ZarrChecksumModification(Path('.'), directories_to_update=[foo]),
            ],
        ),
        (
            [],
            [],
            ['foo', 'foo/bar'],
            [
                ZarrChecksumModification(Path('foo'), paths_to_remove=['foo/bar']),
                ZarrChecksumModification(Path('.'), paths_to_remove=['foo']),
            ],
        ),
        (
            [],
            [foo],
            ['foo/bar'],
            [
                ZarrChecksumModification(Path('foo'), paths_to_remove=['foo/bar']),
                ZarrChecksumModification(Path('.'), directories_to_update=[foo]),
            ],
        ),
        (
            [foo_bar_baz],
            [foo],
            ['foo/bar', 'bar'],
            [
                ZarrChecksumModification(Path('foo/bar'), files_to_update=[foo_bar_baz]),
                ZarrChecksumModification(Path('foo'), paths_to_remove=['foo/bar']),
                ZarrChecksumModification(
                    Path('.'), directories_to_update=[foo], paths_to_remove=['bar']
                ),
            ],
        ),
    ],
)
def test_zarr_checksum_modification_queue(
    file_updates: list[ZarrChecksum],
    directory_updates: list[ZarrChecksum],
    removals: list[Path],
    modifications,
):
    queue = ZarrChecksumModificationQueue()
    for file_update in file_updates:
        queue.queue_file_update(parent_directory_map[file_update.digest], file_update)
    for directory_update in directory_updates:
        queue.queue_directory_update(
            parent_directory_map[directory_update.digest], directory_update
        )
    for removal in removals:
        queue.queue_removal(Path(removal).parent, removal)

    while not queue.empty:
        assert queue.pop_deepest() == modifications[0]
        del modifications[0]

    assert queue.empty
    assert modifications == []


# ZarrChecksumUpdater tests


@pytest.mark.django_db
def test_zarr_checksum_updater(storage, zarr_archive: ZarrArchive, zarr_upload_file_factory):
    a: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive, path='a')
    b: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive, path='b')
    c: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive, path='c')

    # Test update_checksums
    ZarrChecksumUpdater(zarr_archive).update_file_checksums(
        {
            'foo/a': a.to_checksum(),
            'foo/b': b.to_checksum(),
            'foo/bar/c': c.to_checksum(),
        }
    )

    serializer = ZarrJSONChecksumSerializer()
    # There should be 3 checksum files generated: foo/bar, foo, and the top level
    # foo/bar contains an entry for c
    foo_bar_listing = serializer.generate_listing(files=[c.to_checksum()])
    # foo contains an entry for a, b, and bar
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

    assert ZarrChecksumFileUpdater(zarr_archive, 'foo/bar').read_checksum_file() == foo_bar_listing
    assert ZarrChecksumFileUpdater(zarr_archive, 'foo').read_checksum_file() == foo_listing
    assert ZarrChecksumFileUpdater(zarr_archive, '').read_checksum_file() == root_listing

    # Test remove_checksums by removing the deepest file, c
    ZarrChecksumUpdater(zarr_archive).remove_checksums(['foo/bar/c'])
    # There should now only be two checksum files: foo and the top level
    # foo no longer contains bar
    foo_listing = serializer.generate_listing(files=[a.to_checksum(), b.to_checksum()])
    # The root needs to be updated, since foo's checksum has changed
    root_listing = serializer.generate_listing(
        directories=[ZarrChecksum(name='foo', digest=foo_listing.digest, size=200)]
    )

    assert not c.blob.storage.exists(
        ZarrChecksumFileUpdater(zarr_archive, 'foo/bar').checksum_file_path
    )
    assert ZarrChecksumFileUpdater(zarr_archive, 'foo').read_checksum_file() == foo_listing
    assert ZarrChecksumFileUpdater(zarr_archive, '').read_checksum_file() == root_listing
