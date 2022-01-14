from pathlib import Path

import pytest

from dandiapi.api.models import ZarrArchive, ZarrUploadFile
from dandiapi.api.tests.fuzzy import UUID_RE
from dandiapi.api.zarr_checksums import EMPTY_CHECKSUM, ZarrChecksumFileUpdater, ZarrChecksumUpdater


@pytest.mark.django_db
def test_zarr_rest_create(authenticated_api_client):
    name = 'My Zarr File!'

    resp = authenticated_api_client.post('/api/zarr/', {'name': name}, format='json')
    assert resp.json() == {
        'name': name,
        'zarr_id': UUID_RE,
        'checksum': EMPTY_CHECKSUM,
        'file_count': 0,
        'size': 0,
    }
    assert resp.status_code == 200

    zarr_archive = ZarrArchive.objects.get(zarr_id=resp.json()['zarr_id'])
    assert zarr_archive.name == name


@pytest.mark.django_db
def test_zarr_rest_get(
    authenticated_api_client, storage, zarr_archive: ZarrArchive, zarr_upload_file_factory
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload = zarr_upload_file_factory(zarr_archive=zarr_archive)
    # We need to complete the upload for the checksum files to be written.
    zarr_archive.complete_upload()

    resp = authenticated_api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    print(resp.json())
    assert resp.status_code == 200
    assert resp.json() == {
        'name': zarr_archive.name,
        'zarr_id': zarr_archive.zarr_id,
        'checksum': zarr_archive.checksum,
        'file_count': 1,
        'size': upload.size(),
    }


@pytest.mark.django_db
def test_zarr_rest_get_empty(authenticated_api_client, zarr_archive: ZarrArchive):
    resp = authenticated_api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    print(resp.json())
    assert resp.status_code == 200
    assert resp.json() == {
        'name': zarr_archive.name,
        'zarr_id': zarr_archive.zarr_id,
        'checksum': zarr_archive.checksum,
        'file_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_zarr_rest_delete_file(
    authenticated_api_client,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload = zarr_upload_file_factory(zarr_archive=zarr_archive)
    zarr_archive.complete_upload()

    resp = authenticated_api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/', [{'path': upload.path}]
    )
    assert resp.status_code == 204

    assert not upload.blob.field.storage.exists(upload.blob.name)
    zarr_archive.refresh_from_db()
    assert zarr_archive.file_count == 0
    assert zarr_archive.size == 0


@pytest.mark.django_db
def test_zarr_rest_delete_multiple_files(
    authenticated_api_client,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    uploads = [zarr_upload_file_factory(zarr_archive=zarr_archive) for i in range(0, 10)]
    zarr_archive.complete_upload()

    resp = authenticated_api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/', [{'path': upload.path} for upload in uploads]
    )
    assert resp.status_code == 204

    for upload in uploads:
        assert not upload.blob.field.storage.exists(upload.blob.name)
    zarr_archive.refresh_from_db()
    assert zarr_archive.file_count == 0
    assert zarr_archive.size == 0


@pytest.mark.django_db
def test_zarr_rest_delete_missing_file(
    authenticated_api_client,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload = zarr_upload_file_factory(zarr_archive=zarr_archive)
    zarr_archive.complete_upload()

    resp = authenticated_api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [
            {'path': upload.path},
            {'path': 'does/not/exist'},
        ],
    )
    assert resp.status_code == 400
    assert resp.json() == [
        f'File test-prefix/test-zarr/{zarr_archive.zarr_id}/does/not/exist does not exist.'
    ]
    assert upload.blob.field.storage.exists(upload.blob.name)
    zarr_archive.refresh_from_db()
    assert zarr_archive.file_count == 1
    assert zarr_archive.size == upload.size()


@pytest.mark.django_db
def test_zarr_rest_delete_upload_in_progress(
    authenticated_api_client,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload = zarr_upload_file_factory(zarr_archive=zarr_archive)

    resp = authenticated_api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [{'path': upload.path}],
    )
    assert resp.status_code == 400
    assert resp.json() == ['Cannot delete files while an upload is in progress.']


@pytest.mark.parametrize(
    ('path', 'status', 'directories', 'files'),
    [
        ('', 200, ['foo/'], []),
        ('foo/', 200, ['foo/bar/'], ['foo/a', 'foo/b']),
        ('foo/bar/', 200, [], ['foo/bar/c']),
        ('foo', 302, None, None),
        ('foo/a', 302, None, None),
        ('foo/b', 302, None, None),
        ('foo/bar/c', 302, None, None),
        ('gibberish', 302, None, None),
    ],
    ids=[
        'root-dir',
        'foo/-dir',
        'foo/bar/-dir',
        'foo-file',
        'foo/a-file',
        'foo/b-file',
        'foo/bar/c-file',
        'gibberish-file',
    ],
)
@pytest.mark.django_db
def test_zarr_explore(
    api_client,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
    path,
    status,
    directories,
    files,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    a: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive, path='foo/a')
    b: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive, path='foo/b')
    c: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive, path='foo/bar/c')

    # Write the checksum files
    ZarrChecksumUpdater(zarr_archive).update_file_checksums(
        [a.to_checksum(), b.to_checksum(), c.to_checksum()],
    )
    listing = ZarrChecksumFileUpdater(zarr_archive, path).read_checksum_file()

    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}.zarr/{path}',
    )
    assert resp.status_code == status
    if status == 200:
        assert resp.json() == {
            'directories': [
                f'http://localhost:8000/api/zarr/{zarr_archive.zarr_id}.zarr/{dirpath}'
                for dirpath in directories
            ],
            'files': [
                f'http://localhost:8000/api/zarr/{zarr_archive.zarr_id}.zarr/{filepath}'
                for filepath in files
            ],
            'checksums': {
                **{
                    Path(directory.path).name: directory.md5
                    for directory in listing.checksums.directories
                },
                **{Path(file.path).name: file.md5 for file in listing.checksums.files},
            },
            'checksum': listing.md5,
        }
    if status == 302:
        assert resp.headers['Location'].startswith(
            f'http://localhost:9000/test-dandiapi-dandisets/test-prefix/test-zarr/{zarr_archive.zarr_id}/{path}?'  # noqa: E501
        )


@pytest.mark.parametrize(
    'path',
    [
        'foo',
        'foo/a',
        'foo/b',
        'foo/bar/c',
        'gibberish',
    ],
    ids=[
        'foo-file',
        'foo/a-file',
        'foo/b-file',
        'foo/bar/c-file',
        'gibberish-file',
    ],
)
@pytest.mark.django_db
def test_zarr_explore_head(
    api_client,
    storage,
    zarr_archive: ZarrArchive,
    path,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage

    resp = api_client.head(
        f'/api/zarr/{zarr_archive.zarr_id}.zarr/{path}',
    )
    assert resp.status_code == 302
    assert resp.headers['Location'].startswith(
        f'http://localhost:9000/test-dandiapi-dandisets/test-prefix/test-zarr/{zarr_archive.zarr_id}/{path}?'  # noqa: E501
    )
