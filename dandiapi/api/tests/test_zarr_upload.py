import hashlib

from dandischema.digests.zarr import EMPTY_CHECKSUM
from guardian.shortcuts import assign_perm
import pytest
import requests

from dandiapi.api.models import ZarrArchive, ZarrUploadFile
from dandiapi.api.tasks import cancel_zarr_upload
from dandiapi.api.tasks.zarr import ingest_zarr_archive
from dandiapi.api.tests.fuzzy import HTTP_URL_RE


@pytest.mark.django_db
def test_zarr_rest_upload_start(authenticated_api_client, user, zarr_archive: ZarrArchive):
    assign_perm('owner', user, zarr_archive.dandiset)
    path = 'foo/bar.txt'
    text = b'Some fascinating zarr content.\n'
    h = hashlib.md5()
    h.update(text)
    etag = h.hexdigest()

    resp = authenticated_api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/upload/',
        [
            {
                'path': path,
                'etag': etag,
            }
        ],
        format='json',
    )
    assert resp.status_code == 200
    assert resp.json() == [{'path': path, 'upload_url': HTTP_URL_RE}]

    assert ZarrUploadFile.objects.get(path=path, etag=etag)
    assert zarr_archive.upload_in_progress


@pytest.mark.django_db
def test_zarr_rest_upload_start_not_an_owner(authenticated_api_client, zarr_archive: ZarrArchive):
    path = 'foo/bar.txt'
    text = b'Some fascinating zarr content.\n'
    h = hashlib.md5()
    h.update(text)
    etag = h.hexdigest()

    resp = authenticated_api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/upload/',
        [
            {
                'path': path,
                'etag': etag,
            }
        ],
        format='json',
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_rest_upload_start_simultaneous(
    authenticated_api_client,
    user,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    assign_perm('owner', user, zarr_archive.dandiset)
    zarr_upload_file_factory(zarr_archive=zarr_archive)

    path = 'foo/bar.txt'
    text = b'Some fascinating zarr content.\n'
    h = hashlib.md5()
    h.update(text)
    etag = h.hexdigest()

    resp = authenticated_api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/upload/',
        [
            {
                'path': path,
                'etag': etag,
            }
        ],
        format='json',
    )
    assert resp.status_code == 400
    assert resp.json() == ['Simultaneous uploads are not allowed.']


@pytest.mark.django_db
def test_zarr_rest_upload_complete(
    authenticated_api_client,
    user,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    assign_perm('owner', user, zarr_archive.dandiset)
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    # Creating a zarr upload file means that the zarr has an upload in progress
    zarr_upload_file_factory(zarr_archive=zarr_archive)
    assert zarr_archive.upload_in_progress
    assert zarr_archive.checksum == EMPTY_CHECKSUM

    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/upload/complete/')
    assert resp.status_code == 201

    # Completing the upload means that it is no longer in progress
    assert not zarr_archive.upload_in_progress


@pytest.mark.django_db
def test_zarr_rest_upload_complete_not_an_owner(
    authenticated_api_client,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    # Creating a zarr upload file means that the zarr has an upload in progress
    zarr_upload_file_factory(zarr_archive=zarr_archive)
    assert zarr_archive.upload_in_progress
    assert zarr_archive.checksum == EMPTY_CHECKSUM

    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/upload/complete/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_rest_upload_complete_no_upload(
    authenticated_api_client, user, zarr_archive: ZarrArchive
):
    assign_perm('owner', user, zarr_archive.dandiset)
    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/upload/complete/')
    assert resp.status_code == 400
    assert resp.json() == ['No upload in progress.']


@pytest.mark.django_db
def test_zarr_rest_upload_complete_missing_file(
    authenticated_api_client, user, zarr_archive: ZarrArchive
):
    assign_perm('owner', user, zarr_archive.dandiset)
    # Creating a DB entry without creating the corresponding file in S3
    upload = ZarrUploadFile.objects.create_zarr_upload_file(
        zarr_archive=zarr_archive, path='foo/bar.nwb', etag='whatever'
    )
    upload.save()

    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/upload/complete/')
    assert resp.status_code == 400
    assert resp.json() == [f'File {upload.path} does not exist.']


@pytest.mark.django_db
def test_zarr_rest_upload_complete_incorrect_etag(
    authenticated_api_client,
    user,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    assign_perm('owner', user, zarr_archive.dandiset)
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    upload: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive, etag='incorrect')

    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/upload/complete/')
    assert resp.status_code == 400
    assert resp.json() == [
        f'File {upload.path} ETag {upload.actual_etag()} does not match reported checksum {upload.etag}.'  # noqa: E501
    ]


@pytest.mark.django_db(transaction=True)
def test_zarr_rest_upload_cancel(
    authenticated_api_client,
    user,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    assign_perm('owner', user, zarr_archive.dandiset)
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    # Creating a zarr upload file means that the zarr has an upload in progress
    zarr_upload_file: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    assert zarr_upload_file.blob.field.storage.exists(zarr_upload_file.blob.name)
    assert zarr_archive.upload_in_progress

    resp = authenticated_api_client.delete(f'/api/zarr/{zarr_archive.zarr_id}/upload/')
    assert resp.status_code == 204

    # The task was delayed but has not yet started, so nothing has changed
    assert zarr_upload_file.blob.field.storage.exists(zarr_upload_file.blob.name)
    assert zarr_archive.upload_in_progress


@pytest.mark.django_db
def test_zarr_rest_upload_cancel_not_an_owner(
    authenticated_api_client,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    # Creating a zarr upload file means that the zarr has an upload in progress
    zarr_upload_file: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    assert zarr_upload_file.blob.field.storage.exists(zarr_upload_file.blob.name)
    assert zarr_archive.upload_in_progress

    resp = authenticated_api_client.delete(f'/api/zarr/{zarr_archive.zarr_id}/upload/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_rest_upload_cancel_no_upload(
    authenticated_api_client, user, zarr_archive: ZarrArchive
):
    assign_perm('owner', user, zarr_archive.dandiset)
    assert not zarr_archive.upload_in_progress

    resp = authenticated_api_client.delete(f'/api/zarr/{zarr_archive.zarr_id}/upload/')
    assert resp.status_code == 400
    assert resp.json() == ['No upload to cancel.']


@pytest.mark.django_db
def test_zarr_rest_upload_cancel_task(
    authenticated_api_client,
    user,
    storage,
    zarr_archive: ZarrArchive,
    zarr_upload_file_factory,
):
    assign_perm('owner', user, zarr_archive.dandiset)
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage
    # Creating a zarr upload file means that the zarr has an upload in progress
    zarr_upload_file: ZarrUploadFile = zarr_upload_file_factory(zarr_archive=zarr_archive)
    assert zarr_upload_file.blob.field.storage.exists(zarr_upload_file.blob.name)
    assert zarr_archive.upload_in_progress

    cancel_zarr_upload(str(zarr_archive.zarr_id))

    assert not zarr_upload_file.blob.field.storage.exists(zarr_upload_file.blob.name)
    assert not zarr_archive.upload_in_progress


@pytest.mark.django_db
def test_zarr_rest_upload_flow(authenticated_api_client, user, storage, zarr_archive: ZarrArchive):
    assign_perm('owner', user, zarr_archive.dandiset)
    # Pretend like ZarrUploadFile was defined with the given storage
    ZarrUploadFile.blob.field.storage = storage

    path = 'foo/bar.txt'
    text = b'Some fascinating zarr content.\n'
    h = hashlib.md5()
    h.update(text)
    etag = h.hexdigest()

    resp = authenticated_api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/upload/',
        [
            {
                'path': path,
                'etag': etag,
            }
        ],
        format='json',
    )
    upload_url = resp.json()[0]['upload_url']

    resp = requests.put(upload_url, data=text, headers={'X-Amz-ACL': 'bucket-owner-full-control'})
    assert resp.status_code == 200

    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/upload/complete/')
    assert resp.status_code == 201

    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()
    assert not zarr_archive.upload_in_progress
    assert zarr_archive.file_count == 1
    assert zarr_archive.size == len(text)
