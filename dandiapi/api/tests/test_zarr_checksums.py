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
    ZarrChecksums,
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
    'file_checksums,directory_checksums,checksum',
    [
        ([], [], 'deb10f9b7b3275dc058b71f011525789'),
        ([ZarrChecksum(path='foo/bar', md5='a')], [], '5a815bced8a21b433e1074feebbde86e'),
        ([], [ZarrChecksum(path='foo/bar', md5='a')], '5f4c8223552adf78f375063e42874328'),
        (
            [ZarrChecksum(path='foo/bar', md5='a'), ZarrChecksum(path='foo/baz', md5='b')],
            [],
            'b2a825702d706090faf13fd18cc2db99',
        ),
        (
            [],
            [ZarrChecksum(path='foo/bar', md5='a'), ZarrChecksum(path='foo/baz', md5='b')],
            '176ebfa3adc85bd2c428297fc39c2334',
        ),
        (
            [ZarrChecksum(path='foo/baz', md5='a')],
            [ZarrChecksum(path='foo/bar', md5='b')],
            '437319759d2ab0e6f62ef5ca7a9b822a',
        ),
    ],
)
def test_zarr_checksum_serializer_aggregate_checksum(file_checksums, directory_checksums, checksum):
    serializer = ZarrJSONChecksumSerializer()
    assert (
        serializer.aggregate_checksum(
            ZarrChecksums(files=file_checksums, directories=directory_checksums)
        )
        == checksum
    )


def test_zarr_checksum_serializer_generate_listing():
    serializer = ZarrJSONChecksumSerializer()
    checksums = ZarrChecksums(
        files=[ZarrChecksum(path='foo/bar', md5='a')],
        directories=[ZarrChecksum(path='foo/baz', md5='b')],
    )
    assert serializer.generate_listing(checksums) == ZarrChecksumListing(
        checksums=checksums, md5='a1dc945351c72ecacd237063d68f5eb4'
    )


def test_zarr_serialize():
    serializer = ZarrJSONChecksumSerializer()
    assert (
        serializer.serialize(
            ZarrChecksumListing(
                checksums=ZarrChecksums(
                    files=[ZarrChecksum(path='foo/bar', md5='a')],
                    directories=[ZarrChecksum(path='bar/foo', md5='b')],
                ),
                md5='c',
            )
        )
        == '{"checksums":{"files":[{"path":"foo/bar","md5":"a"}],"directories":[{"path":"bar/foo","md5":"b"}]},"md5":"c"}'  # noqa: E501
    )


def test_zarr_deserialize():
    serializer = ZarrJSONChecksumSerializer()
    assert serializer.deserialize(
        '{"checksums":{"files":[{"path":"foo/bar","md5":"a"}],"directories":[{"path":"bar/foo","md5":"b"}]},"md5":"c"}'  # noqa: E501
    ) == ZarrChecksumListing(
        checksums=ZarrChecksums(
            files=[ZarrChecksum(path='foo/bar', md5='a')],
            directories=[ZarrChecksum(path='bar/foo', md5='b')],
        ),
        md5='c',
    )


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
        checksums=ZarrChecksums(
            files=[
                upload.to_checksum(),
            ]
        ),
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
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    upload_parent_path = str(Path(upload.path).parent)
    listing = ZarrChecksumListing(checksums=ZarrChecksums(files=[upload.to_checksum()]), md5='b')

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
    listing = serializer.generate_listing(files=checksums)

    updater = ZarrChecksumFileUpdater(zarr_archive, upload_parent_path)
    updater.write_checksum_file(listing)

    with ZarrChecksumFileUpdater(zarr_archive, upload_parent_path) as updater:
        # Initializing the context manager loads the checksum file
        assert updater.checksum_listing == listing

        # Add two new checksums to the updater
        a = ZarrChecksum(path='foo/bar', md5='a')
        b = ZarrChecksum(path='foo/baz', md5='b')
        # Duplicate checksums should be removed
        updater.add_file_checksums(sorted([upload.to_checksum(), a, a, b, b]))
        # The updater's internal state should be updated
        assert updater.checksum_listing == serializer.generate_listing(
            files=sorted(checksums + [a, b])
        )

        # Remove the A checksum from the updater
        # The md5 should not need to match
        updater.remove_checksums([a.path])
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


foo = ZarrChecksum(path='foo', md5='md5')
bar = ZarrChecksum(path='bar', md5='md5')
foo_bar = ZarrChecksum(path='foo/bar', md5='md5')
foo_bar_baz = ZarrChecksum(path='foo/bar/baz', md5='md5')


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
        queue.queue_file_update(Path(file_update.path).parent, file_update)
    for directory_update in directory_updates:
        queue.queue_directory_update(Path(directory_update.path).parent, directory_update)
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
    ZarrChecksumUpdater(zarr_archive).update_file_checksums(
        [a.to_checksum(), b.to_checksum(), c.to_checksum()],
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
            ZarrChecksum(path='foo/bar', md5=foo_bar_listing.md5),
        ],
    )
    # The root contains an entry for foo
    root_listing = serializer.generate_listing(
        directories=[
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
    foo_listing = serializer.generate_listing(files=[a.to_checksum(), b.to_checksum()])
    # The root needs to be updated, since foo's checksum has changed
    root_listing = serializer.generate_listing(
        directories=[ZarrChecksum(path='foo', md5=foo_listing.md5)]
    )

    assert not c.blob.storage.exists(
        ZarrChecksumFileUpdater(zarr_archive, 'foo/bar').checksum_file_path
    )
    assert ZarrChecksumFileUpdater(zarr_archive, 'foo').read_checksum_file() == foo_listing
    assert ZarrChecksumFileUpdater(zarr_archive, '').read_checksum_file() == root_listing
