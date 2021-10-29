from __future__ import annotations

from pathlib import Path

import pytest

from dandiapi.api.models import ZarrArchive, ZarrUploadFile
from dandiapi.api.zarr_checksums import (
    ZarrChecksum,
    ZarrChecksumFileUpdater,
    ZarrChecksumListing,
    ZarrChecksumModification,
    ZarrChecksumModificationQueue,
    ZarrChecksumUpdater,
    ZarrJSONChecksumSerializer,
)


def test_zarr_checksum_sort_order():
    # The a < b in the path should take precedence over z > y in the md5
    a = ZarrChecksum(path='1/2/3/a/z', md5='z')
    b = ZarrChecksum(path='1/2/3/b/z', md5='y')
    assert sorted([b, a]) == [a, b]


# ZarrJSONChecksumSerializer tests


@pytest.mark.parametrize(
    'checksums,checksum',
    [
        ([], 'd751713988987e9331980363e24189ce'),
        ([ZarrChecksum(path='foo/bar', md5='a')], '44a6ca7f9a269dbb286790b119f849a6'),
        (
            [ZarrChecksum(path='foo/bar', md5='a'), ZarrChecksum(path='foo/baz', md5='b')],
            '487cb4605eb53f8e38728d7791db02f5',
        ),
        (
            [ZarrChecksum(path='foo/baz', md5='b'), ZarrChecksum(path='foo/bar', md5='a')],
            '487cb4605eb53f8e38728d7791db02f5',
        ),
    ],
)
def test_zarr_checksum_serializer_aggregate_checksum(checksums, checksum):
    serializer = ZarrJSONChecksumSerializer()
    assert serializer.aggregate_checksum(checksums) == checksum


def test_zarr_checksum_serializer_generate_listing():
    serializer = ZarrJSONChecksumSerializer()
    checksums = [ZarrChecksum(path='foo/bar', md5='a'), ZarrChecksum(path='foo/baz', md5='b')]
    assert serializer.generate_listing(checksums) == ZarrChecksumListing(
        checksums=checksums, md5='487cb4605eb53f8e38728d7791db02f5'
    )


def test_zarr_serialize():
    serializer = ZarrJSONChecksumSerializer()
    assert (
        serializer.serialize(
            ZarrChecksumListing(checksums=[ZarrChecksum(path='foo/bar', md5='a')], md5='b')
        )
        == '{"checksums": [{"path": "foo/bar", "md5": "a"}], "md5": "b"}'
    )


def test_zarr_deserialize():
    serializer = ZarrJSONChecksumSerializer()
    assert serializer.deserialize(
        '{"checksums": [{"path": "foo/bar", "md5": "a"}], "md5": "b"}'
    ) == ZarrChecksumListing(checksums=[ZarrChecksum(path='foo/bar', md5='a')], md5='b')


# ZarrChecksumFileUpdater tests


@pytest.mark.django_db
def test_zarr_checksum_file_updater_checksum_file_path(
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
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
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    upload_parent_path = str(Path(upload.path).parent)
    listing = ZarrChecksumListing(
        checksums=[
            upload.to_checksum(),
        ],
        md5='b',
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
    listing.checksums.append(second_upload.to_checksum())

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
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    upload_parent_path = str(Path(upload.path).parent)
    listing = ZarrChecksumListing(checksums=[upload.to_checksum()], md5='b')

    updater = ZarrChecksumFileUpdater(zarr_archive, upload_parent_path)
    updater.write_checksum_file(listing)
    assert updater.read_checksum_file() == listing


@pytest.mark.django_db
def test_zarr_checksum_file_updater_delete_checksum_file(
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
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
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    upload_parent_path = str(Path(upload.path).parent)
    serializer = ZarrJSONChecksumSerializer()
    checksums = [upload.to_checksum()]
    listing = serializer.generate_listing(checksums)

    updater = ZarrChecksumFileUpdater(zarr_archive, upload_parent_path)
    updater.write_checksum_file(listing)

    with ZarrChecksumFileUpdater(zarr_archive, upload_parent_path) as updater:
        # Initializing the context manager loads the checksum file
        assert updater.checksum_listing == listing

        # Add two new checksums to the updater
        a = ZarrChecksum(path='foo/bar', md5='a')
        b = ZarrChecksum(path='foo/baz', md5='b')
        # Duplicate checksums should be removed
        updater.add_checksums([upload.to_checksum(), a, a, b, b])
        # The updater's internal state should be updated
        assert updater.checksum_listing == serializer.generate_listing(checksums + [a, b])

        # Remove the A checksum from the updater
        # The md5 should not need to match
        updater.remove_checksums([a.path])
        assert updater.checksum_listing == serializer.generate_listing(checksums + [b])

        # The file should not yet be updated with our changes
        assert updater.read_checksum_file() == serializer.generate_listing(checksums)

    # Exiting the context should write the checksum file
    assert updater.read_checksum_file() == serializer.generate_listing(checksums + [b])


# ZarrChecksumModificationQueue tests


foo = ZarrChecksum('foo', 'md5')
bar = ZarrChecksum('bar', 'md5')
foo_bar = ZarrChecksum('foo/bar', 'md5')
foo_bar_baz = ZarrChecksum('foo/bar/baz', 'md5')


@pytest.mark.parametrize(
    'updates,removals,modifications',
    [
        (
            [foo],
            [],
            [ZarrChecksumModification(Path('.'), checksums_to_update=[foo])],
        ),
        (
            [],
            ['foo'],
            [ZarrChecksumModification(Path('.'), paths_to_remove=['foo'])],
        ),
        (
            [foo, bar],
            [],
            [ZarrChecksumModification(Path('.'), checksums_to_update=[foo, bar])],
        ),
        (
            [foo, foo_bar],
            [],
            [
                ZarrChecksumModification(Path('foo'), checksums_to_update=[foo_bar]),
                ZarrChecksumModification(Path('.'), checksums_to_update=[foo]),
            ],
        ),
        (
            [],
            ['foo', 'foo/bar'],
            [
                ZarrChecksumModification(Path('foo'), paths_to_remove=['foo/bar']),
                ZarrChecksumModification(Path('.'), paths_to_remove=['foo']),
            ],
        ),
        (
            [foo],
            ['foo/bar'],
            [
                ZarrChecksumModification(Path('foo'), paths_to_remove=['foo/bar']),
                ZarrChecksumModification(Path('.'), checksums_to_update=[foo]),
            ],
        ),
        (
            [foo, foo_bar_baz],
            ['foo/bar', 'bar'],
            [
                ZarrChecksumModification(Path('foo/bar'), checksums_to_update=[foo_bar_baz]),
                ZarrChecksumModification(Path('foo'), paths_to_remove=['foo/bar']),
                ZarrChecksumModification(
                    Path('.'), checksums_to_update=[foo], paths_to_remove=['bar']
                ),
            ],
        ),
    ],
)
def test_zarr_checksum_modification_queue(
    updates: list[ZarrChecksum],
    removals: list[Path],
    modifications,
):
    queue = ZarrChecksumModificationQueue()
    for update in updates:
        queue.queue_update(Path(update.path).parent, update)
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
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    a: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive, path='foo/a')
    b: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive, path='foo/b')
    c: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive, path='foo/bar/c')

    # Test update_checksums
    ZarrChecksumUpdater(zarr_archive).update_checksums(
        [a.to_checksum(), b.to_checksum(), c.to_checksum()]
    )

    serializer = ZarrJSONChecksumSerializer()
    # There should be 3 checksum files generated: foo/bar, foo, and the top level
    # foo/bar contains an entry for c
    foo_bar_listing = serializer.generate_listing([c.to_checksum()])
    # foo contains an entry for a, b, and bar
    foo_listing = serializer.generate_listing(
        [
            a.to_checksum(),
            b.to_checksum(),
            ZarrChecksum(path='foo/bar', md5=foo_bar_listing.md5),
        ]
    )
    # The root contains an entry for foo
    root_listing = serializer.generate_listing(
        [
            ZarrChecksum(path='foo', md5=foo_listing.md5),
        ]
    )

    assert ZarrChecksumFileUpdater(zarr_archive, 'foo/bar').read_checksum_file() == foo_bar_listing
    assert ZarrChecksumFileUpdater(zarr_archive, 'foo').read_checksum_file() == foo_listing
    assert ZarrChecksumFileUpdater(zarr_archive, '').read_checksum_file() == root_listing

    # Test remove_checksums by removing the deepest file, c
    ZarrChecksumUpdater(zarr_archive).remove_checksums(['foo/bar/c'])
    # There should now only be two checksum files: foo and the top level
    # foo no longer contains bar
    foo_listing = serializer.generate_listing([a.to_checksum(), b.to_checksum()])
    # The root needs to be updated, since foo's checksum has changed
    root_listing = serializer.generate_listing([ZarrChecksum(path='foo', md5=foo_listing.md5)])

    assert not c.blob.storage.exists(
        ZarrChecksumFileUpdater(zarr_archive, 'foo/bar').checksum_file_path
    )
    assert ZarrChecksumFileUpdater(zarr_archive, 'foo').read_checksum_file() == foo_listing
    assert ZarrChecksumFileUpdater(zarr_archive, '').read_checksum_file() == root_listing
