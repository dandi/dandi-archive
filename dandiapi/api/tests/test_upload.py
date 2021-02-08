import pytest
import requests

from dandiapi.api.models import Validation

from .fuzzy import HTTP_URL_RE, UUID_RE, Re


def mb(bytes_size: int) -> int:
    return bytes_size * 2 ** 20


@pytest.mark.django_db
def test_upload_initialize(api_client, user):
    api_client.force_authenticate(user=user)

    file_name = 'test.txt'
    file_size = 123

    assert api_client.post(
        '/api/uploads/initialize/',
        {'file_name': file_name, 'file_size': file_size},
        format='json',
    ).data == {
        'object_key': Re(f'{file_name}/[a-z0-9\\-]+'),
        'upload_id': UUID_RE,
        'parts': [
            {
                'part_number': 1,
                'size': file_size,
                'upload_url': HTTP_URL_RE,
            }
        ],
    }


@pytest.mark.django_db
def test_upload_initialize_unauthorized(api_client):
    assert (
        api_client.post(
            '/api/uploads/initialize/',
            {},
            format='json',
        ).status_code
        == 401
    )


@pytest.mark.django_db
def test_upload_complete(api_client, user):
    api_client.force_authenticate(user=user)

    file_name = 'test.txt'
    file_size = 123

    assert api_client.post(
        '/api/uploads/complete/',
        {
            'object_key': file_name,
            'upload_id': 'test-uuid',
            'parts': [{'part_number': 1, 'size': file_size, 'etag': 'test-etag'}],
        },
        format='json',
    ).data == {
        'complete_url': HTTP_URL_RE,
        'body': Re(r'.*'),
    }


@pytest.mark.django_db
def test_upload_complete_unauthorized(api_client):
    assert (
        api_client.post(
            '/api/uploads/complete/',
            {},
            format='json',
        ).status_code
        == 401
    )


@pytest.mark.django_db
@pytest.mark.parametrize('file_size', [10, mb(10), mb(12)], ids=['10B', '10MB', '12MB'])
def test_upload_initialize_and_complete(api_client, user, file_size):
    api_client.force_authenticate(user=user)

    file_name = 'upload-test.txt'

    # Get the presigned upload URL
    initialization = api_client.post(
        '/api/uploads/initialize/',
        {'file_name': file_name, 'file_size': file_size},
        format='json',
    ).data

    object_key = initialization['object_key']
    upload_id = initialization['upload_id']
    parts = initialization['parts']

    # Send the data directly to the object store
    transferred_parts = []
    part_number = 1
    for part in parts:
        part_transfer = requests.put(part['upload_url'], data=b'X' * part['size'])
        etag = part_transfer.headers['etag']
        transferred_parts.append({'part_number': part_number, 'size': part['size'], 'etag': etag})
        part_number += 1

    # Get the presigned complete URL
    completion = api_client.post(
        '/api/uploads/complete/',
        {
            'object_key': object_key,
            'upload_id': upload_id,
            'parts': transferred_parts,
        },
        format='json',
    ).data

    # Complete the upload to the object store
    completion_response = requests.post(completion['complete_url'], data=completion['body'])
    assert completion_response.status_code == 200

    # Verify object was uploaded
    assert Validation.blob.field.storage.exists(object_key)
