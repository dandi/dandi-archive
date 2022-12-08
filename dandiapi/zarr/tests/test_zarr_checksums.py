from __future__ import annotations

from pathlib import Path

from dandischema.digests.zarr import (
    ZarrChecksum,
    ZarrChecksumListing,
    ZarrChecksums,
    ZarrJSONChecksumSerializer,
)
import pytest

from dandiapi.zarr.checksums import ZarrChecksumModification, ZarrChecksumModificationQueue


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
