from __future__ import annotations

import uuid

import pytest
import requests
from zarr_checksum.checksum import EMPTY_CHECKSUM

from dandiapi.api.tests.factories import UserFactory
from dandiapi.api.tests.fuzzy import HTTP_URL_RE, Re
from dandiapi.zarr.models import ZarrArchiveStatus, ZarrUpload, ZarrUploadType
from dandiapi.zarr.tests.factories import (
    EmbargoedZarrArchiveFactory,
    ZarrArchiveFactory,
    ZarrUploadFactory,
)


def initialize_body(zarr_archive, chunk_key: str = '0/chunk', content_size: int = 100) -> dict:
    return {
        'contentSize': content_size,
        'digest': {'algorithm': 'dandi:dandi-etag', 'value': 'f' * 32 + '-1'},
        'zarr_id': str(zarr_archive.zarr_id),
        'chunk_key': chunk_key,
    }


@pytest.mark.django_db
@pytest.mark.parametrize('embargoed', [True, False])
def test_zarr_multipart_upload_initialize(api_client, embargoed):
    user = UserFactory.create()
    factory = EmbargoedZarrArchiveFactory if embargoed else ZarrArchiveFactory
    zarr_archive = factory.create(dandiset__owners=[user], upload_type=ZarrUploadType.MULTIPART)
    api_client.force_authenticate(user=user)

    chunk_key = '0/chunk'
    resp = api_client.post(
        '/api/zarr/uploads/initialize/', initialize_body(zarr_archive, chunk_key=chunk_key)
    )
    assert resp.status_code == 200
    assert 'upload_id' in resp.data
    assert 'parts' in resp.data

    upload = ZarrUpload.objects.get(upload_id=resp.data['upload_id'])
    assert upload.zarr == zarr_archive
    assert upload.chunk_key == chunk_key
    assert upload.blob.name == zarr_archive.s3_path(chunk_key)
    assert upload.embargoed == embargoed


@pytest.mark.django_db
def test_zarr_multipart_upload_initialize_single_part_rejected(api_client):
    """Multipart upload to a single-part zarr must be rejected."""
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create(
        dandiset__owners=[user], upload_type=ZarrUploadType.SINGLEPART
    )

    resp = api_client.post('/api/zarr/uploads/initialize/', initialize_body(zarr_archive))
    assert resp.status_code == 400
    assert not ZarrUpload.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize('status', [ZarrArchiveStatus.UPLOADED, ZarrArchiveStatus.INGESTING])
def test_zarr_multipart_upload_initialize_ingesting(api_client, status):
    """Uploading to a zarr that's already been finalized must be rejected."""
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create(
        dandiset__owners=[user], upload_type=ZarrUploadType.MULTIPART, status=status
    )

    resp = api_client.post('/api/zarr/uploads/initialize/', initialize_body(zarr_archive))
    assert resp.status_code == 400
    assert not ZarrUpload.objects.exists()


@pytest.mark.django_db
def test_zarr_multipart_upload_initialize_not_an_owner(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create(upload_type=ZarrUploadType.MULTIPART)

    resp = api_client.post('/api/zarr/uploads/initialize/', initialize_body(zarr_archive))
    assert resp.status_code == 403
    assert not ZarrUpload.objects.exists()


@pytest.mark.django_db
def test_zarr_multipart_upload_initialize_zarr_not_found(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    resp = api_client.post(
        '/api/zarr/uploads/initialize/',
        {
            'contentSize': 100,
            'digest': {'algorithm': 'dandi:dandi-etag', 'value': 'f' * 32 + '-1'},
            'zarr_id': str(uuid.uuid4()),
            'chunk_key': 'some/key',
        },
    )
    assert resp.status_code == 404
    assert not ZarrUpload.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_zarr_multipart_upload_complete(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_upload = ZarrUploadFactory.create()

    assert api_client.post(
        f'/api/zarr/uploads/{zarr_upload.upload_id}/complete/',
        {'parts': [{'part_number': 1, 'size': 100, 'etag': 'test-etag'}]},
    ).data == {
        'complete_url': HTTP_URL_RE,
        'body': Re(r'.*'),
    }


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('chunk_key', ['.zattrs', '0/0/0'])
def test_zarr_multipart_upload_validate(api_client, chunk_key):
    """Validating a zarr upload returns the zarr ID and chunk key."""
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr = ZarrArchiveFactory.create(
        upload_type=ZarrUploadType.MULTIPART,
        status=ZarrArchiveStatus.COMPLETE,
        checksum=EMPTY_CHECKSUM,
    )
    zarr_upload = ZarrUploadFactory.create(zarr=zarr, chunk_key=chunk_key)

    resp = api_client.post(f'/api/zarr/uploads/{zarr_upload.upload_id}/validate/')
    assert resp.status_code == 200
    assert resp.data == {'zarr_id': str(zarr.zarr_id), 'chunk_key': chunk_key}

    assert not ZarrUpload.objects.exists()

    # Check that zarr is now in a `PENDING` state
    zarr.refresh_from_db()
    assert zarr.status == ZarrArchiveStatus.PENDING
    assert zarr.checksum is None


@pytest.mark.django_db(transaction=True)
def test_zarr_multipart_upload_initialize_and_complete(api_client):
    user = UserFactory.create()
    zarr_archive = ZarrArchiveFactory.create(
        dandiset__owners=[user], upload_type=ZarrUploadType.MULTIPART
    )
    api_client.force_authenticate(user=user)

    chunk_key = '0/chunk'
    initialization = api_client.post(
        '/api/zarr/uploads/initialize/', initialize_body(zarr_archive, chunk_key=chunk_key)
    ).data

    upload_id = initialization['upload_id']
    transferred_parts = []
    for part_number, part in enumerate(initialization['parts'], start=1):
        part_transfer = requests.put(part['upload_url'], data=b'X' * part['size'], timeout=5)
        transferred_parts.append(
            {
                'part_number': part_number,
                'size': part['size'],
                'etag': part_transfer.headers['etag'],
            }
        )

    completion = api_client.post(
        f'/api/zarr/uploads/{upload_id}/complete/',
        {'parts': transferred_parts},
    ).data

    completion_response = requests.post(
        completion['complete_url'], data=completion['body'], timeout=5
    )
    assert completion_response.status_code == 200

    upload = ZarrUpload.objects.get(upload_id=upload_id)
    assert upload.blob.storage.exists(upload.blob.name)
    assert upload.blob.name == zarr_archive.s3_path(chunk_key)
    assert upload.zarr == zarr_archive
