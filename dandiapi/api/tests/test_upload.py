import hashlib

from django.core.files.base import ContentFile
import pytest
import requests

from dandiapi.api.models import Validation

from .fuzzy import HTTP_URL_RE, TIMESTAMP_RE, UUID_RE, Re


def mb(bytes_size: int) -> int:
    return bytes_size * 2 ** 20


@pytest.mark.django_db
def test_upload_initialize(api_client, user):
    api_client.force_authenticate(user=user)

    file_name = 'test.txt'
    file_size = 123

    assert api_client.post(
        '/api/uploads/initialize/',
        {'file_name': file_name, 'file_size': file_size, 'sha256': 'test-sha256'},
        format='json',
    ).data == {
        'object_key': file_name,
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
        == 403
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
        == 403
    )


@pytest.mark.django_db
@pytest.mark.parametrize('file_size', [10, mb(10), mb(12)], ids=['10B', '10MB', '12MB'])
def test_upload_initialize_and_complete(api_client, user, file_size):
    api_client.force_authenticate(user=user)

    file_name = 'upload-test.txt'

    # Get the presigned upload URL
    initialization = api_client.post(
        '/api/uploads/initialize/',
        {'file_name': file_name, 'file_size': file_size, 'sha256': 'test-sha256'},
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


@pytest.mark.django_db
def test_validate(api_client, user):
    api_client.force_authenticate(user=user)

    object_key = 'test.txt'
    contents = b'test content'

    h = hashlib.sha256()
    h.update(contents)
    sha256 = h.hexdigest()

    Validation.blob.field.storage.save(object_key, ContentFile(contents))

    assert (
        api_client.post(
            '/api/uploads/validate/',
            {
                'object_key': object_key,
                'sha256': sha256,
            },
            format='json',
        ).status_code
        == 204
    )

    validation = Validation.objects.get(sha256=sha256)
    assert validation.blob.name == object_key
    assert validation.state == Validation.State.IN_PROGRESS

    # TODO how to test that the celery job kicked off?


@pytest.mark.django_db
@pytest.mark.parametrize('state', [Validation.State.SUCCEEDED, Validation.State.FAILED])
def test_validate_old_validation(api_client, user, state):
    api_client.force_authenticate(user=user)

    object_key = 'test.txt'
    contents = b'test content'

    h = hashlib.sha256()
    h.update(contents)
    sha256 = h.hexdigest()

    Validation.blob.field.storage.save(object_key, ContentFile(contents))

    # Save an existing Validation that will be updated
    Validation(blob=object_key, sha256=sha256, state=state).save()

    assert (
        api_client.post(
            '/api/uploads/validate/',
            {
                'object_key': object_key,
                'sha256': sha256,
            },
            format='json',
        ).status_code
        == 204
    )

    validation = Validation.objects.get(sha256=sha256)
    assert validation.blob.name == object_key
    assert validation.state == Validation.State.IN_PROGRESS


@pytest.mark.django_db
def test_validate_in_progress_validation(api_client, user):
    api_client.force_authenticate(user=user)

    object_key = 'test.txt'
    contents = b'test content'

    h = hashlib.sha256()
    h.update(contents)
    sha256 = h.hexdigest()

    Validation.blob.field.storage.save(object_key, ContentFile(contents))

    # Save an existing Validation that will be updated
    Validation(blob=object_key, sha256=sha256, state=Validation.State.IN_PROGRESS).save()

    resp = api_client.post(
        '/api/uploads/validate/',
        {
            'object_key': object_key,
            'sha256': sha256,
        },
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == ['Validation already in progress']


@pytest.mark.django_db
def test_validate_object_does_not_exist(api_client, user):
    api_client.force_authenticate(user=user)

    object_key = 'does-not-exist.txt'
    contents = b'test content'

    h = hashlib.sha256()
    h.update(contents)
    sha256 = h.hexdigest()

    resp = api_client.post(
        '/api/uploads/validate/',
        {
            'object_key': object_key,
            'sha256': sha256,
        },
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == ['Object does not exist']


@pytest.mark.django_db
@pytest.mark.parametrize(
    'state', [Validation.State.IN_PROGRESS, Validation.State.SUCCEEDED, Validation.State.FAILED]
)
def test_get_validation(api_client, user, state):
    api_client.force_authenticate(user=user)

    object_key = 'does-not-exist.txt'
    contents = b'test content'

    h = hashlib.sha256()
    h.update(contents)
    sha256 = h.hexdigest()

    # Save an existing Validation that will be updated
    Validation(blob=object_key, sha256=sha256, state=state).save()

    assert api_client.get(
        f'/api/uploads/validations/{sha256}/',
        {
            'object_key': object_key,
            'sha256': sha256,
        },
        format='json',
    ).data == {
        'state': str(state),
        'sha256': sha256,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
    }
