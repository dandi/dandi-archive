from __future__ import annotations

import os
import uuid

from django.core.files.base import ContentFile
from guardian.shortcuts import assign_perm
import pytest
import requests

from dandiapi.api.models import AssetBlob, Dandiset, EmbargoedAssetBlob, EmbargoedUpload, Upload

from .fuzzy import HTTP_URL_RE, UUID_RE, Re


def mb(bytes_size: int) -> int:
    return bytes_size * 2**20


@pytest.mark.django_db()
def test_blob_read(api_client, asset_blob):
    assert api_client.post(
        '/api/blobs/digest/',
        {'algorithm': 'dandi:dandi-etag', 'value': asset_blob.etag},
        format='json',
    ).data == {
        'blob_id': str(asset_blob.blob_id),
        'etag': asset_blob.etag,
        'sha256': asset_blob.sha256,
        'size': asset_blob.size,
    }


@pytest.mark.django_db()
def test_blob_read_sha256(api_client, asset_blob):
    assert api_client.post(
        '/api/blobs/digest/',
        {'algorithm': 'dandi:sha2-256', 'value': asset_blob.sha256},
        format='json',
    ).data == {
        'blob_id': str(asset_blob.blob_id),
        'etag': asset_blob.etag,
        'sha256': asset_blob.sha256,
        'size': asset_blob.size,
    }


@pytest.mark.django_db()
def test_blob_read_bad_algorithm(api_client, asset_blob):
    resp = api_client.post(
        '/api/blobs/digest/',
        {'algorithm': 'sha256', 'value': asset_blob.sha256},
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == 'Unsupported Digest Algorithm. Supported: dandi:dandi-etag, dandi:sha2-256'


@pytest.mark.django_db()
def test_blob_read_does_not_exist(api_client):
    resp = api_client.post(
        '/api/blobs/digest/',
        {'algorithm': 'dandi:dandi-etag', 'value': 'not etag'},
        format='json',
    )
    assert resp.status_code == 404


@pytest.mark.django_db()
def test_upload_initialize(api_client, user, dandiset):
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, dandiset)

    content_size = 123

    resp = api_client.post(
        '/api/uploads/initialize/',
        {
            'contentSize': content_size,
            'digest': {'algorithm': 'dandi:dandi-etag', 'value': 'f' * 32 + '-1'},
            'dandiset': dandiset.identifier,
        },
        format='json',
    )
    assert resp.data == {
        'upload_id': UUID_RE,
        'parts': [
            {
                'part_number': 1,
                'size': content_size,
                'upload_url': HTTP_URL_RE,
            }
        ],
    }
    # Verify that the URL won't expire for a week
    upload_url = resp.data['parts'][0]['upload_url']
    # 604800 seconds = 1 week
    assert 'X-Amz-Expires=604800' in upload_url

    upload = Upload.objects.get(upload_id=resp.data['upload_id'])
    upload_id = str(upload.upload_id)
    assert upload.blob.name == f'test-prefix/blobs/{upload_id[:3]}/{upload_id[3:6]}/{upload_id}'


@pytest.mark.django_db()
def test_upload_initialize_existing_asset_blob(api_client, user, dandiset, asset_blob):
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, dandiset)

    resp = api_client.post(
        '/api/uploads/initialize/',
        {
            'contentSize': asset_blob.size,
            'digest': {'algorithm': 'dandi:dandi-etag', 'value': asset_blob.etag},
            'dandiset': dandiset.identifier,
        },
        format='json',
    )
    assert resp.status_code == 409
    assert resp.data == 'Blob already exists.'
    assert resp.get('Location') == str(asset_blob.blob_id)
    assert not Upload.objects.all().exists()


@pytest.mark.django_db()
def test_upload_initialize_not_an_owner(api_client, user, dandiset):
    api_client.force_authenticate(user=user)

    content_size = 123

    resp = api_client.post(
        '/api/uploads/initialize/',
        {
            'contentSize': content_size,
            'digest': {'algorithm': 'dandi:dandi-etag', 'value': 'f' * 32 + '-1'},
            'dandiset': dandiset.identifier,
        },
        format='json',
    )
    assert resp.status_code == 403
    assert not Upload.objects.all().exists()
    assert not EmbargoedUpload.objects.all().exists()


@pytest.mark.django_db()
def test_upload_initialize_embargo(api_client, user, dandiset_factory):
    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, dandiset)

    content_size = 123

    resp = api_client.post(
        '/api/uploads/initialize/',
        {
            'contentSize': content_size,
            'digest': {'algorithm': 'dandi:dandi-etag', 'value': 'f' * 32 + '-1'},
            'dandiset': dandiset.identifier,
        },
        format='json',
    )
    assert resp.data == {
        'upload_id': UUID_RE,
        'parts': [
            {
                'part_number': 1,
                'size': content_size,
                'upload_url': HTTP_URL_RE,
            }
        ],
    }
    # Verify that the URL won't expire for a week
    upload_url = resp.data['parts'][0]['upload_url']
    # 604800 seconds = 1 week
    assert 'X-Amz-Expires=604800' in upload_url

    assert not Upload.objects.all().exists()
    upload = EmbargoedUpload.objects.get(upload_id=resp.data['upload_id'])
    upload_id = str(upload.upload_id)
    assert upload.blob.name == (
        f'test-embargo-prefix/{dandiset.identifier}/blobs/'
        f'{upload_id[:3]}/{upload_id[3:6]}/{upload_id}'
    )


@pytest.mark.django_db()
def test_upload_initialize_embargo_not_an_owner(api_client, user, dandiset_factory):
    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    # user is not an owner of the embargoed dandiset, so the embargoed dandiset "doesn't exist"

    content_size = 123

    resp = api_client.post(
        '/api/uploads/initialize/',
        {
            'contentSize': content_size,
            'digest': {'algorithm': 'dandi:dandi-etag', 'value': 'f' * 32 + '-1'},
            'dandiset': dandiset.identifier,
        },
        format='json',
    )
    assert resp.status_code == 404
    assert resp.json() == {'detail': 'Not found.'}
    assert not Upload.objects.all().exists()
    assert not EmbargoedUpload.objects.all().exists()


@pytest.mark.django_db()
def test_upload_initialize_embargo_existing_asset_blob(
    api_client, user, dandiset_factory, asset_blob
):
    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, dandiset)

    # Embargoed assets that are already uploaded publicly don't need to be private
    resp = api_client.post(
        '/api/uploads/initialize/',
        {
            'contentSize': asset_blob.size,
            'digest': {'algorithm': 'dandi:dandi-etag', 'value': asset_blob.etag},
            'dandiset': dandiset.identifier,
        },
        format='json',
    )
    assert resp.status_code == 409
    assert resp.data == 'Blob already exists.'
    assert resp.get('Location') == str(asset_blob.blob_id)
    assert not Upload.objects.all().exists()


@pytest.mark.django_db()
def test_upload_initialize_embargo_existing_embargoed_asset_blob(
    api_client, user, dandiset_factory, embargoed_asset_blob_factory
):
    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, dandiset)
    # This EmbargoedAssetBlob is in the same embargoed dandiset, so it should be deduplicated
    embargoed_asset_blob = embargoed_asset_blob_factory(dandiset=dandiset)

    resp = api_client.post(
        '/api/uploads/initialize/',
        {
            'contentSize': embargoed_asset_blob.size,
            'digest': {'algorithm': 'dandi:dandi-etag', 'value': embargoed_asset_blob.etag},
            'dandiset': dandiset.identifier,
        },
        format='json',
    )
    assert resp.status_code == 409
    assert resp.data == 'Blob already exists.'
    assert resp.get('Location') == str(embargoed_asset_blob.blob_id)
    assert not Upload.objects.all().exists()


@pytest.mark.django_db()
def test_upload_initialize_embargo_existing_embargoed_asset_blob_in_different_dandiset(
    api_client, user, dandiset_factory, embargoed_asset_blob_factory
):
    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, dandiset)
    other_dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    # This EmbargoedAssetBlob is in a different dandiset, so it needs to be reuploaded, even
    # though this user is an owner of both dandisets.
    embargoed_asset_blob = embargoed_asset_blob_factory(dandiset=other_dandiset)
    assign_perm('owner', user, other_dandiset)

    resp = api_client.post(
        '/api/uploads/initialize/',
        {
            'contentSize': embargoed_asset_blob.size,
            'digest': {'algorithm': 'dandi:dandi-etag', 'value': embargoed_asset_blob.etag},
            'dandiset': dandiset.identifier,
        },
        format='json',
    )
    assert resp.status_code == 200


@pytest.mark.django_db()
def test_upload_initialize_unauthorized(api_client):
    assert (
        api_client.post(
            '/api/uploads/initialize/',
            {},
            format='json',
        ).status_code
        == 401
    )


@pytest.mark.django_db(transaction=True)
def test_upload_complete(api_client, user, upload):
    api_client.force_authenticate(user=user)

    content_size = 123

    assert api_client.post(
        f'/api/uploads/{upload.upload_id}/complete/',
        {
            'parts': [{'part_number': 1, 'size': content_size, 'etag': 'test-etag'}],
        },
        format='json',
    ).data == {
        'complete_url': HTTP_URL_RE,
        'body': Re(r'.*'),
    }


@pytest.mark.django_db(transaction=True)
def test_upload_complete_embargo(api_client, user, dandiset_factory, embargoed_upload_factory):
    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, dandiset)
    embargoed_upload = embargoed_upload_factory(dandiset=dandiset)

    content_size = 123

    assert api_client.post(
        f'/api/uploads/{embargoed_upload.upload_id}/complete/',
        {
            'parts': [{'part_number': 1, 'size': content_size, 'etag': 'test-etag'}],
        },
        format='json',
    ).data == {
        'complete_url': HTTP_URL_RE,
        'body': Re(r'.*'),
    }


@pytest.mark.django_db(transaction=True)
def test_upload_complete_embargo_not_an_owner(
    api_client, user, dandiset_factory, embargoed_upload_factory
):
    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    embargoed_upload = embargoed_upload_factory(dandiset=dandiset)
    # The user doesn't own the dandiset being uploaded to, so they cannot complete the upload.

    content_size = 123

    assert (
        api_client.post(
            f'/api/uploads/{embargoed_upload.upload_id}/complete/',
            {
                'parts': [{'part_number': 1, 'size': content_size, 'etag': 'test-etag'}],
            },
            format='json',
        ).status_code
        == 404
    )


@pytest.mark.django_db(transaction=True)
def test_upload_complete_unauthorized(api_client, upload):
    assert (
        api_client.post(
            f'/api/uploads/{upload.upload_id}/complete/',
            {},
            format='json',
        ).status_code
        == 401
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('content_size', [10, mb(10), mb(12)], ids=['10B', '10MB', '12MB'])
def test_upload_initialize_and_complete(api_client, user, dandiset, content_size):
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, dandiset)

    # Get the presigned upload URL
    initialization = api_client.post(
        '/api/uploads/initialize/',
        {
            'contentSize': content_size,
            'digest': {'algorithm': 'dandi:dandi-etag', 'value': 'f' * 32 + '-1'},
            'dandiset': dandiset.identifier,
        },
        format='json',
    ).data

    upload_id = initialization['upload_id']
    parts = initialization['parts']

    # Send the data directly to the object store
    transferred_parts = []
    part_number = 1
    for part in parts:
        part_transfer = requests.put(part['upload_url'], data=b'X' * part['size'], timeout=5)
        etag = part_transfer.headers['etag']
        transferred_parts.append({'part_number': part_number, 'size': part['size'], 'etag': etag})
        part_number += 1

    # Get the presigned complete URL
    completion = api_client.post(
        f'/api/uploads/{upload_id}/complete/',
        {
            'parts': transferred_parts,
        },
        format='json',
    ).data

    # Complete the upload to the object store
    completion_response = requests.post(
        completion['complete_url'], data=completion['body'], timeout=5
    )
    assert completion_response.status_code == 200

    # Verify object was uploaded
    upload = Upload.objects.get(upload_id=upload_id)
    assert AssetBlob.blob.field.storage.exists(upload.blob.name)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize('content_size', [10, mb(10), mb(12)], ids=['10B', '10MB', '12MB'])
def test_upload_initialize_and_complete_embargo(
    storage, api_client, user, dandiset_factory, content_size
):
    # Pretend like the blobs were defined with the given storage
    EmbargoedUpload.blob.field.storage = storage
    EmbargoedAssetBlob.blob.field.storage = storage

    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, dandiset)

    # Get the presigned upload URL
    initialization = api_client.post(
        '/api/uploads/initialize/',
        {
            'contentSize': content_size,
            'digest': {'algorithm': 'dandi:dandi-etag', 'value': 'f' * 32 + '-1'},
            'dandiset': dandiset.identifier,
        },
        format='json',
    ).data

    upload_id = initialization['upload_id']
    parts = initialization['parts']

    # Send the data directly to the object store
    transferred_parts = []
    part_number = 1
    for part in parts:
        part_transfer = requests.put(part['upload_url'], data=b'X' * part['size'], timeout=5)
        etag = part_transfer.headers['etag']
        transferred_parts.append({'part_number': part_number, 'size': part['size'], 'etag': etag})
        part_number += 1

    # Get the presigned complete URL
    completion = api_client.post(
        f'/api/uploads/{upload_id}/complete/',
        {
            'parts': transferred_parts,
        },
        format='json',
    ).data

    # Complete the upload to the object store
    completion_response = requests.post(
        completion['complete_url'], data=completion['body'], timeout=5
    )
    assert completion_response.status_code == 200

    # Verify object was uploaded
    upload = EmbargoedUpload.objects.get(upload_id=upload_id)
    assert EmbargoedAssetBlob.blob.field.storage.exists(upload.blob.name)
    assert upload.blob.name.startswith(f'test-embargo-prefix/{dandiset.identifier}/blobs/')
    # Verify nothing public was created
    assert not Upload.objects.all().exists()


@pytest.mark.django_db(transaction=True)
def test_upload_validate(api_client, user, upload):
    api_client.force_authenticate(user=user)

    resp = api_client.post(f'/api/uploads/{upload.upload_id}/validate/')
    assert resp.status_code == 200
    assert resp.data == {
        'blob_id': str(upload.upload_id),
        'etag': upload.etag,
        'sha256': None,
        'size': upload.size,
    }

    # Verify that a new AssetBlob was created
    asset_blob = AssetBlob.objects.get(blob_id=upload.upload_id)
    assert asset_blob.blob.name == upload.blob.name

    # Verify that the Upload was deleted
    assert not Upload.objects.all().exists()


@pytest.mark.django_db(transaction=True)
def test_upload_validate_embargo(api_client, user, dandiset_factory, embargoed_upload_factory):
    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, dandiset)
    embargoed_upload = embargoed_upload_factory(dandiset=dandiset)

    resp = api_client.post(f'/api/uploads/{embargoed_upload.upload_id}/validate/')
    assert resp.status_code == 200
    assert resp.data == {
        'blob_id': str(embargoed_upload.upload_id),
        'etag': embargoed_upload.etag,
        'sha256': None,
        'size': embargoed_upload.size,
    }

    # Verify that a new EmbargoedAssetBlob was created
    embargoed_asset_blob = EmbargoedAssetBlob.objects.get(blob_id=embargoed_upload.upload_id)
    assert embargoed_asset_blob.blob.name == embargoed_upload.blob.name

    # Verify that the Upload was deleted
    assert not EmbargoedUpload.objects.all().exists()


@pytest.mark.django_db(transaction=True)
def test_upload_validate_upload_missing(api_client, user, upload):
    api_client.force_authenticate(user=user)

    upload.blob.delete(upload.blob.name)

    resp = api_client.post(f'/api/uploads/{upload.upload_id}/validate/')
    assert resp.status_code == 400
    assert resp.data == ['Object does not exist.']

    assert not AssetBlob.objects.all().exists()
    assert Upload.objects.all().exists()


@pytest.mark.django_db(transaction=True)
def test_upload_validate_wrong_size(api_client, user, upload):
    api_client.force_authenticate(user=user)

    wrong_content = b'not 100 bytes'
    upload.blob.save(os.path.basename(upload.blob.name), ContentFile(wrong_content))

    resp = api_client.post(f'/api/uploads/{upload.upload_id}/validate/')
    assert resp.status_code == 400
    assert resp.data == [f'Size {upload.size} does not match actual size {len(wrong_content)}.']

    assert not AssetBlob.objects.all().exists()
    assert Upload.objects.all().exists()


@pytest.mark.django_db(transaction=True)
def test_upload_validate_wrong_etag(api_client, user, upload):
    api_client.force_authenticate(user=user)

    actual_etag = upload.etag
    upload.etag = uuid.uuid4()
    upload.save()

    resp = api_client.post(f'/api/uploads/{upload.upload_id}/validate/')
    assert resp.status_code == 400
    assert resp.data == [f'ETag {upload.etag} does not match actual ETag {actual_etag}.']

    assert not AssetBlob.objects.all().exists()
    assert Upload.objects.all().exists()


@pytest.mark.django_db(transaction=True)
def test_upload_validate_existing_assetblob(api_client, user, upload, asset_blob_factory):
    api_client.force_authenticate(user=user)

    asset_blob = asset_blob_factory(etag=upload.etag, size=upload.size)

    resp = api_client.post(f'/api/uploads/{upload.upload_id}/validate/')
    assert resp.status_code == 200
    assert resp.data == {
        'blob_id': str(asset_blob.blob_id),
        'etag': asset_blob.etag,
        'sha256': asset_blob.sha256,
        'size': asset_blob.size,
    }

    assert AssetBlob.objects.all().count() == 1
    assert not Upload.objects.all().exists()


@pytest.mark.django_db(transaction=True)
def test_upload_validate_embargo_existing_assetblob(
    api_client, user, dandiset_factory, embargoed_upload_factory, asset_blob_factory
):
    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, dandiset)
    embargoed_upload = embargoed_upload_factory(dandiset=dandiset)

    # The upload should recognize this preexisting AssetBlob and use it instead
    asset_blob = asset_blob_factory(etag=embargoed_upload.etag, size=embargoed_upload.size)

    resp = api_client.post(f'/api/uploads/{embargoed_upload.upload_id}/validate/')
    assert resp.status_code == 200
    assert resp.data == {
        'blob_id': str(asset_blob.blob_id),
        'etag': asset_blob.etag,
        'sha256': asset_blob.sha256,
        'size': asset_blob.size,
    }

    assert AssetBlob.objects.all().count() == 1
    assert not EmbargoedAssetBlob.objects.all().exists()
    assert not EmbargoedUpload.objects.all().exists()


@pytest.mark.django_db(transaction=True)
def test_upload_validate_embargo_existing_embargoedassetblob(
    api_client, user, dandiset_factory, embargoed_upload_factory, embargoed_asset_blob_factory
):
    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, dandiset)
    embargoed_upload = embargoed_upload_factory(dandiset=dandiset)

    # The upload should recognize this preexisting EmbargoedAssetBlob and use it instead
    # This only works because the embargoed asset blob belongs to the same dandiset
    embargoed_asset_blob = embargoed_asset_blob_factory(
        etag=embargoed_upload.etag, size=embargoed_upload.size, dandiset=dandiset
    )

    resp = api_client.post(f'/api/uploads/{embargoed_upload.upload_id}/validate/')
    assert resp.status_code == 200
    assert resp.data == {
        'blob_id': str(embargoed_asset_blob.blob_id),
        'etag': embargoed_asset_blob.etag,
        'sha256': embargoed_asset_blob.sha256,
        'size': embargoed_asset_blob.size,
    }

    assert EmbargoedAssetBlob.objects.all().count() == 1
    assert not AssetBlob.objects.all().exists()
    assert not EmbargoedUpload.objects.all().exists()


@pytest.mark.django_db(transaction=True)
def test_upload_validate_embargo_existing_embargoedassetblob_wrong_dandiset(
    api_client, user, dandiset_factory, embargoed_upload_factory, embargoed_asset_blob_factory
):
    api_client.force_authenticate(user=user)
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, dandiset)
    embargoed_upload = embargoed_upload_factory(dandiset=dandiset)

    # This should mint a new EmbargoedAssetBlob because the existing EmbargoedAssetBlob belongs to
    # a different dandiset.
    other_dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    assign_perm('owner', user, other_dandiset)
    other_embargoed_asset_blob = embargoed_asset_blob_factory(
        etag=embargoed_upload.etag, size=embargoed_upload.size, dandiset=other_dandiset
    )

    resp = api_client.post(f'/api/uploads/{embargoed_upload.upload_id}/validate/')
    assert resp.status_code == 200
    assert resp.data == {
        'blob_id': str(embargoed_upload.upload_id),
        'etag': embargoed_upload.etag,
        'sha256': None,
        'size': embargoed_upload.size,
    }

    # Verify that a new EmbargoedAssetBlob was created
    embargoed_asset_blob = EmbargoedAssetBlob.objects.get(blob_id=embargoed_upload.upload_id)
    assert embargoed_asset_blob.blob.name == embargoed_upload.blob.name
    assert embargoed_asset_blob.blob_id != other_embargoed_asset_blob.blob_id
    assert EmbargoedAssetBlob.objects.count() == 2

    # Verify that the Upload was deleted
    assert not EmbargoedUpload.objects.all().exists()
