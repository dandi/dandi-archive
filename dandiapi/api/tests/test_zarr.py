from pathlib import Path

from dandischema.digests.zarr import EMPTY_CHECKSUM
from django.conf import settings
from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.models import ZarrArchive, ZarrUploadFile
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.tasks.zarr import ingest_zarr_archive
from dandiapi.api.tests.fuzzy import UUID_RE
from dandiapi.api.zarr_checksums import ZarrChecksumFileUpdater, ZarrChecksumUpdater


@pytest.mark.django_db
def test_zarr_rest_create(authenticated_api_client, user, dandiset):
    assign_perm('owner', user, dandiset)
    name = 'My Zarr File!'

    resp = authenticated_api_client.post(
        '/api/zarr/',
        {
            'name': name,
            'dandiset': dandiset.identifier,
        },
        format='json',
    )
    assert resp.json() == {
        'name': name,
        'zarr_id': UUID_RE,
        'dandiset': dandiset.identifier,
        'status': ZarrArchive.Status.PENDING,
        'checksum': EMPTY_CHECKSUM,
        'upload_in_progress': False,
        'file_count': 0,
        'size': 0,
    }
    assert resp.status_code == 200

    zarr_archive = ZarrArchive.objects.get(zarr_id=resp.json()['zarr_id'])
    assert zarr_archive.name == name


@pytest.mark.django_db
def test_zarr_rest_create_not_an_owner(authenticated_api_client, zarr_archive):
    resp = authenticated_api_client.post(
        '/api/zarr/',
        {
            'name': zarr_archive.name,
            'dandiset': zarr_archive.dandiset.identifier,
        },
        format='json',
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_rest_create_duplicate(authenticated_api_client, user, zarr_archive):
    assign_perm('owner', user, zarr_archive.dandiset)
    resp = authenticated_api_client.post(
        '/api/zarr/',
        {
            'name': zarr_archive.name,
            'dandiset': zarr_archive.dandiset.identifier,
        },
        format='json',
    )
    assert resp.status_code == 400
    assert resp.json() == ['Zarr already exists']


@pytest.mark.django_db
def test_zarr_rest_create_embargoed_dandiset(
    authenticated_api_client,
    user,
    zarr_archive,
    dandiset_factory,
):
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, dandiset)
    resp = authenticated_api_client.post(
        '/api/zarr/',
        {
            'name': zarr_archive.name,
            'dandiset': dandiset.identifier,
        },
        format='json',
    )
    assert resp.status_code == 400
    assert resp.json() == ['Cannot add zarr to embargoed dandiset']


@pytest.mark.django_db
def test_zarr_rest_get(
    authenticated_api_client, storage, zarr_archive: ZarrArchive, zarr_upload_file_factory
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload = zarr_upload_file_factory(zarr_archive=zarr_archive)
    # We need to complete the upload for the checksum files to be written.
    zarr_archive.complete_upload()

    # Ingest archive so checksum files are written.
    ingest_zarr_archive(zarr_archive.zarr_id)

    resp = authenticated_api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    assert resp.status_code == 200
    assert resp.json() == {
        'name': zarr_archive.name,
        'zarr_id': zarr_archive.zarr_id,
        'dandiset': zarr_archive.dandiset.identifier,
        'status': ZarrArchive.Status.COMPLETE,
        'checksum': zarr_archive.checksum,
        'upload_in_progress': False,
        'file_count': 1,
        'size': upload.size(),
    }


@pytest.mark.django_db
def test_zarr_rest_get_very_big(authenticated_api_client, zarr_archive_factory):
    ten_quadrillion = 10**16
    ten_petabytes = 10**16
    zarr_archive = zarr_archive_factory(file_count=ten_quadrillion, size=ten_petabytes)
    assert zarr_archive.file_count == ten_quadrillion
    assert zarr_archive.size == ten_petabytes

    # Don't ingest since there aren't actually any files
    resp = authenticated_api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    assert resp.status_code == 200
    assert resp.json() == {
        'name': zarr_archive.name,
        'zarr_id': zarr_archive.zarr_id,
        'dandiset': zarr_archive.dandiset.identifier,
        'status': ZarrArchive.Status.PENDING,
        'checksum': zarr_archive.checksum,
        'upload_in_progress': False,
        'file_count': ten_quadrillion,
        'size': ten_petabytes,
    }


@pytest.mark.django_db
def test_zarr_rest_get_empty(authenticated_api_client, zarr_archive: ZarrArchive):
    resp = authenticated_api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    assert resp.status_code == 200
    assert resp.json() == {
        'name': zarr_archive.name,
        'zarr_id': zarr_archive.zarr_id,
        'dandiset': zarr_archive.dandiset.identifier,
        'status': ZarrArchive.Status.PENDING,
        'checksum': zarr_archive.checksum,
        'upload_in_progress': False,
        'file_count': 0,
        'size': 0,
    }


@pytest.mark.django_db
def test_zarr_rest_delete_file(
    authenticated_api_client,
    user,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    assign_perm('owner', user, zarr_archive.dandiset)
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload = zarr_upload_file_factory(zarr_archive=zarr_archive)
    zarr_archive.complete_upload()

    # Ingest
    ingest_zarr_archive(zarr_archive.zarr_id)

    # Assert file count and size
    zarr_archive.refresh_from_db()
    assert zarr_archive.file_count == 1
    assert zarr_archive.size == 100

    # Make delete call
    resp = authenticated_api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/', [{'path': upload.path}]
    )
    assert resp.status_code == 204

    assert not upload.blob.field.storage.exists(upload.blob.name)

    # Re-ingest
    ingest_zarr_archive(zarr_archive.zarr_id)

    zarr_archive.refresh_from_db()
    assert zarr_archive.file_count == 0
    assert zarr_archive.size == 0


@pytest.mark.django_db
def test_zarr_rest_delete_file_asset_metadata(
    authenticated_api_client,
    user,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
    asset_factory,
):
    assign_perm('owner', user, zarr_archive.dandiset)
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload = zarr_upload_file_factory(zarr_archive=zarr_archive)
    zarr_archive.complete_upload()
    asset = asset_factory(zarr=zarr_archive, blob=None)
    ingest_zarr_archive(zarr_archive.zarr_id)

    asset.refresh_from_db()
    zarr_archive.refresh_from_db()
    assert asset.metadata['digest'] == zarr_archive.digest
    assert asset.metadata['contentSize'] == 100

    resp = authenticated_api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/', [{'path': upload.path}]
    )
    assert resp.status_code == 204

    ingest_zarr_archive(zarr_archive.zarr_id)
    asset.refresh_from_db()
    assert asset.metadata['digest']['dandi:dandi-zarr-checksum'] == EMPTY_CHECKSUM
    assert asset.metadata['contentSize'] == 0


@pytest.mark.django_db
def test_zarr_rest_delete_file_not_an_owner(
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
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_rest_delete_multiple_files(
    authenticated_api_client,
    user,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    assign_perm('owner', user, zarr_archive.dandiset)
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

    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()
    assert zarr_archive.file_count == 0
    assert zarr_archive.size == 0


@pytest.mark.django_db
def test_zarr_rest_delete_missing_file(
    authenticated_api_client,
    user,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    assign_perm('owner', user, zarr_archive.dandiset)
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

    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()
    assert zarr_archive.file_count == 1
    assert zarr_archive.size == upload.size()


@pytest.mark.django_db
def test_zarr_rest_delete_upload_in_progress(
    authenticated_api_client,
    user,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    assign_perm('owner', user, zarr_archive.dandiset)
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
    ('path', 'directories', 'files'),
    [
        ('', ['foo/'], []),
        ('foo/', ['foo/bar/'], ['foo/a', 'foo/b']),
        ('foo/bar/', [], ['foo/bar/c']),
    ],
    ids=[
        '/',
        'foo/',
        'foo/bar/',
    ],
)
@pytest.mark.django_db
def test_zarr_explore_directory(
    api_client,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
    path,
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
    assert resp.status_code == 200
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


@pytest.mark.django_db
def test_zarr_explore_directory_does_not_exist(
    api_client,
    storage,
    zarr_archive: ZarrArchive,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}.zarr/does/not/exist/',
    )
    assert resp.status_code == 404


@pytest.mark.parametrize(
    'path',
    [
        'foo',
        'foo/a',
        'foo/b',
        'foo/bar/c',
        'gibberish',
    ],
)
@pytest.mark.django_db
def test_zarr_explore_file(
    api_client,
    storage,
    zarr_archive: ZarrArchive,
    path,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}.zarr/{path}',
    )
    assert resp.status_code == 302
    assert resp.headers['Location'].startswith(
        f'http://{settings.MINIO_STORAGE_ENDPOINT}/test-dandiapi-dandisets/test-prefix/test-zarr/{zarr_archive.zarr_id}/{path}?'  # noqa: E501
    )


@pytest.mark.parametrize(
    'path',
    [
        'foo',
        'foo/a',
        'foo/b',
        'foo/bar/c',
        'gibberish',
        'gibberish/',
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
        f'http://{settings.MINIO_STORAGE_ENDPOINT}/test-dandiapi-dandisets/test-prefix/test-zarr/{zarr_archive.zarr_id}/{path}?'  # noqa: E501
    )
