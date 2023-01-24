from dandischema.digests.zarr import EMPTY_CHECKSUM
from django.conf import settings
from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.tests.fuzzy import UUID_RE
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus, ZarrUploadFile
from dandiapi.zarr.tasks import ingest_zarr_archive


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
        'status': ZarrArchiveStatus.PENDING,
        'checksum': None,
        'upload_in_progress': False,
        'file_count': 0,
        'size': 0,
    }
    assert resp.status_code == 200

    zarr_archive = ZarrArchive.objects.get(zarr_id=resp.json()['zarr_id'])
    assert zarr_archive.name == name


@pytest.mark.django_db
def test_zarr_rest_dandiset_malformed(authenticated_api_client, user, dandiset):
    assign_perm('owner', user, dandiset)
    resp = authenticated_api_client.post(
        '/api/zarr/',
        {
            'name': 'My Zarr File!',
            'dandiset': f'{dandiset.identifier}asd',
        },
        format='json',
    )
    assert resp.status_code == 400
    assert resp.json() == {'dandiset': ['This value does not match the required pattern.']}


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
    zarr_archive.complete_upload()

    # Ingest
    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()

    resp = authenticated_api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    assert resp.status_code == 200
    assert resp.json() == {
        'name': zarr_archive.name,
        'zarr_id': str(zarr_archive.zarr_id),
        'dandiset': zarr_archive.dandiset.identifier,
        'status': ZarrArchiveStatus.COMPLETE,
        'checksum': zarr_archive.checksum,
        'upload_in_progress': False,
        'file_count': 1,
        'size': upload.size(),
    }


@pytest.mark.django_db
def test_zarr_rest_list_filter(authenticated_api_client, dandiset_factory, zarr_archive_factory):
    # Create dandisets and zarrs
    dandiset_a: Dandiset = dandiset_factory()
    zarr_archive_a_a: ZarrArchive = zarr_archive_factory(dandiset=dandiset_a, name='test')
    zarr_archive_a_b: ZarrArchive = zarr_archive_factory(dandiset=dandiset_a, name='unique')

    dandiset_b: Dandiset = dandiset_factory()
    zarr_archive_b_a: ZarrArchive = zarr_archive_factory(dandiset=dandiset_b, name='test')
    zarr_archive_b_b: ZarrArchive = zarr_archive_factory(dandiset=dandiset_b, name='unique2')

    # Test dandiset filter with dandiset a
    resp = authenticated_api_client.get('/api/zarr/', {'dandiset': dandiset_a.identifier})
    assert resp.status_code == 200
    results = resp.json()['results']
    assert len(results) == 2
    assert results[0]['zarr_id'] == zarr_archive_a_a.zarr_id
    assert results[1]['zarr_id'] == zarr_archive_a_b.zarr_id

    # Test dandiset filter with dandiset b
    resp = authenticated_api_client.get('/api/zarr/', {'dandiset': dandiset_b.identifier})
    assert resp.status_code == 200
    results = resp.json()['results']
    assert len(results) == 2
    assert results[0]['zarr_id'] == zarr_archive_b_a.zarr_id
    assert results[1]['zarr_id'] == zarr_archive_b_b.zarr_id

    # Test name filter
    resp = authenticated_api_client.get('/api/zarr/', {'name': 'test'})
    assert resp.status_code == 200
    results = resp.json()['results']
    assert len(results) == 2
    assert results[0]['zarr_id'] == zarr_archive_a_a.zarr_id
    assert results[1]['zarr_id'] == zarr_archive_b_a.zarr_id

    # Test dandiset and name filter
    resp = authenticated_api_client.get('/api/zarr/', {'dandiset': dandiset_b, 'name': 'test'})
    assert resp.status_code == 200
    results = resp.json()['results']
    assert len(results) == 1
    assert results[0]['zarr_id'] == zarr_archive_b_a.zarr_id


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
        'status': ZarrArchiveStatus.PENDING,
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
        'status': ZarrArchiveStatus.PENDING,
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

    # Assert zarr is back in pending state
    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.PENDING
    assert zarr_archive.checksum is None
    assert zarr_archive.file_count == 0
    assert zarr_archive.size == 0

    # Re-ingest
    ingest_zarr_archive(zarr_archive.zarr_id)

    zarr_archive.refresh_from_db()
    assert zarr_archive.checksum == EMPTY_CHECKSUM
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


@pytest.mark.django_db
def test_zarr_file_list(api_client, storage, zarr_archive: ZarrArchive, zarr_upload_file_factory):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage

    files = [
        'foo/bar/a.txt',
        'foo/bar/b.txt',
        'foo/baz.txt',
        # These two files are here just to demonstrate filtering
        'bar/a.txt',
        'bar/b.txt',
    ]
    for file in files:
        zarr_upload_file_factory(zarr_archive=zarr_archive, path=file)

    # Check base listing
    resp = api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/files/')
    assert [x['Key'] for x in resp.json()['results']] == sorted(files)

    # Check that prefix query param works as expected
    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        {'prefix': 'foo/'},
    )
    assert [x['Key'] for x in resp.json()['results']] == [
        'foo/bar/a.txt',
        'foo/bar/b.txt',
        'foo/baz.txt',
    ]

    # Check that prefix and after work together
    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        {'prefix': 'foo/', 'after': 'foo/bar/a.txt'},
    )
    assert [x['Key'] for x in resp.json()['results']] == ['foo/bar/b.txt', 'foo/baz.txt']

    # Use limit query param
    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        {'prefix': 'foo/', 'after': 'foo/bar/a.txt', 'limit': 1},
    )
    assert [x['Key'] for x in resp.json()['results']] == ['foo/bar/b.txt']

    # Check download flag
    resp = api_client.get(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        {'prefix': 'foo/bar/a.txt', 'download': True},
    )
    assert resp.status_code == 302
    assert resp.headers['Location'].startswith(
        f'http://{settings.MINIO_STORAGE_ENDPOINT}/test-dandiapi-dandisets/test-prefix/test-zarr/{zarr_archive.zarr_id}/foo/bar/a.txt?'  # noqa: E501
    )


@pytest.mark.django_db
def test_zarr_explore_head(api_client, storage, zarr_archive: ZarrArchive):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage

    filepath = 'foo/bar.txt'
    resp = api_client.head(f'/api/zarr/{zarr_archive.zarr_id}/files/', {'prefix': filepath})
    assert resp.status_code == 302
    assert resp.headers['Location'].startswith(
        f'http://{settings.MINIO_STORAGE_ENDPOINT}/test-dandiapi-dandisets/test-prefix/test-zarr/{zarr_archive.zarr_id}/{filepath}?'  # noqa: E501
    )
