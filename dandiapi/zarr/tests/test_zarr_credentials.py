from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import pytest
from zarr_checksum.checksum import EMPTY_CHECKSUM

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.tests.factories import UserFactory
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus
from dandiapi.zarr.tests.factories import ZarrArchiveFactory

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


def _embargo_status(*, embargoed: bool) -> str:
    return Dandiset.EmbargoStatus.EMBARGOED if embargoed else Dandiset.EmbargoStatus.OPEN


def _s3_client(credentials_response: dict[str, Any]) -> S3Client:
    """Create an S3 client, as an end user would from the credentials endpoint's response."""
    credentials = credentials_response['credentials']
    return boto3.client(
        's3',
        endpoint_url=credentials_response['endpoint_url'],
        region_name=credentials_response['region'],
        aws_access_key_id=credentials['access_key_id'],
        aws_secret_access_key=credentials['secret_access_key'],
        aws_session_token=credentials['session_token'],
        config=Config(signature_version='s3v4'),
    )


def _put_object(
    client: S3Client, credentials_response: dict[str, Any], key: str, *, tags: dict[str, str]
) -> None:
    bucket = credentials_response['bucket']
    if tags:
        client.put_object(Bucket=bucket, Key=key, Body=b'a', Tagging=urlencode(tags))
    else:
        # An empty "Tagging" would still be sent as a header, so it must be omitted entirely
        client.put_object(Bucket=bucket, Key=key, Body=b'a')


def _assert_access_denied(exc_info: pytest.ExceptionInfo[ClientError]) -> None:
    assert exc_info.value.response['Error']['Code'] == 'AccessDenied'


@pytest.mark.django_db
@pytest.mark.parametrize('embargoed', [False, True])
def test_zarr_rest_credentials(
    api_client,
    zarr_archive_factory,
    embargoed: bool,  # noqa: FBT001
):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = zarr_archive_factory(
        dandiset__owners=[user],
        dandiset__embargo_status=_embargo_status(embargoed=embargoed),
        # Set as complete, to mimic past upload
        status=ZarrArchiveStatus.COMPLETE,
        checksum=EMPTY_CHECKSUM,
        file_count=1,
        size=100,
    )

    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/credentials/')
    assert resp.status_code == 200
    data = resp.json()
    assert data['bucket'] == ZarrArchive.storage.bucket_name
    assert data['prefix'] == zarr_archive.s3_path('')
    assert data['region'] == ZarrArchive.storage.region_name
    assert data['endpoint_url'] == ZarrArchive.storage.endpoint_url
    assert data['object_tags'] == ({'embargoed': 'true'} if embargoed else {})
    assert set(data['credentials']) == {
        'access_key_id',
        'secret_access_key',
        'session_token',
        'expiration',
    }
    expiration = parse_datetime(data['credentials']['expiration'])
    assert expiration is not None
    assert expiration > timezone.now()

    # The zarr could now be changed, so it must be reset
    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.PENDING
    assert zarr_archive.checksum is None
    assert zarr_archive.file_count == 0
    assert zarr_archive.size == 0

    # The credentials can upload and delete within the zarr
    client = _s3_client(data)
    object_path = zarr_archive.s3_path('foo/bar.txt')
    _put_object(client, data, object_path, tags=data['object_tags'])
    assert ZarrArchive.storage.exists(object_path)
    assert ZarrArchive.storage.get_tags(object_path) == data['object_tags']

    client.delete_object(Bucket=data['bucket'], Key=object_path)
    assert not ZarrArchive.storage.exists(object_path)


@pytest.mark.django_db
@pytest.mark.parametrize('embargoed', [False, True])
def test_zarr_rest_credentials_restricted_to_zarr(
    api_client,
    zarr_archive_factory,
    zarr_file_factory,
    embargoed: bool,  # noqa: FBT001
):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = zarr_archive_factory(
        dandiset__owners=[user],
        dandiset__embargo_status=_embargo_status(embargoed=embargoed),
    )
    # Another zarr in the same dandiset, which the user also owns
    other_zarr_archive = zarr_archive_factory(dandiset=zarr_archive.dandiset)
    other_zarr_file = zarr_file_factory(zarr_archive=other_zarr_archive)
    other_object_path = other_zarr_archive.s3_path(str(other_zarr_file.path))

    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/credentials/')
    assert resp.status_code == 200
    data = resp.json()
    client = _s3_client(data)

    with pytest.raises(ClientError) as exc_info:
        _put_object(
            client, data, other_zarr_archive.s3_path('foo/bar.txt'), tags=data['object_tags']
        )
    _assert_access_denied(exc_info)
    assert not ZarrArchive.storage.exists(other_zarr_archive.s3_path('foo/bar.txt'))

    with pytest.raises(ClientError) as exc_info:
        client.delete_object(Bucket=data['bucket'], Key=other_object_path)
    _assert_access_denied(exc_info)
    assert ZarrArchive.storage.exists(other_object_path)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('embargoed', 'tags'),
    [
        # An upload to an open zarr must not be tagged as embargoed
        (False, {'embargoed': 'true'}),
        # An upload to an embargoed zarr must be tagged as embargoed
        (True, {}),
        (True, {'embargoed': 'false'}),
    ],
)
def test_zarr_rest_credentials_enforce_object_tags(
    api_client,
    zarr_archive_factory,
    embargoed: bool,  # noqa: FBT001
    tags: dict[str, str],
):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = zarr_archive_factory(
        dandiset__owners=[user],
        dandiset__embargo_status=_embargo_status(embargoed=embargoed),
    )

    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/credentials/')
    assert resp.status_code == 200
    data = resp.json()
    client = _s3_client(data)
    object_path = zarr_archive.s3_path('foo/bar.txt')

    with pytest.raises(ClientError) as exc_info:
        _put_object(client, data, object_path, tags=tags)
    _assert_access_denied(exc_info)
    assert not ZarrArchive.storage.exists(object_path)


@pytest.mark.django_db
def test_zarr_rest_credentials_embargoed_tag_cannot_be_removed(api_client, zarr_archive_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = zarr_archive_factory(
        dandiset__owners=[user],
        dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED,
    )

    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/credentials/')
    assert resp.status_code == 200
    data = resp.json()
    client = _s3_client(data)
    object_path = zarr_archive.s3_path('foo/bar.txt')
    _put_object(client, data, object_path, tags=data['object_tags'])

    with pytest.raises(ClientError) as exc_info:
        client.put_object_tagging(Bucket=data['bucket'], Key=object_path, Tagging={'TagSet': []})
    _assert_access_denied(exc_info)

    with pytest.raises(ClientError) as exc_info:
        client.delete_object_tagging(Bucket=data['bucket'], Key=object_path)
    _assert_access_denied(exc_info)

    assert ZarrArchive.storage.get_tags(object_path) == {'embargoed': 'true'}


@pytest.mark.django_db
def test_zarr_rest_credentials_unauthenticated(api_client):
    zarr_archive = ZarrArchiveFactory.create()

    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/credentials/')
    assert resp.status_code == 401


@pytest.mark.django_db
def test_zarr_rest_credentials_not_an_owner(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create()

    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/credentials/')
    assert resp.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize('status', [ZarrArchiveStatus.UPLOADED, ZarrArchiveStatus.INGESTING])
def test_zarr_rest_credentials_ingesting(api_client, status: ZarrArchiveStatus):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create(dandiset__owners=[user], status=status)

    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/credentials/')
    assert resp.status_code == 400
    assert resp.json() == ZarrArchive.INGEST_ERROR_MSG

    zarr_archive.refresh_from_db()
    assert zarr_archive.status == status


@pytest.mark.django_db
def test_zarr_rest_credentials_unembargo_in_progress(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create(
        dandiset__owners=[user],
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING,
        # Set as complete, to verify that the zarr is left unchanged
        status=ZarrArchiveStatus.COMPLETE,
        checksum=EMPTY_CHECKSUM,
    )

    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/credentials/')
    assert resp.status_code == 400

    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.COMPLETE


@pytest.mark.django_db
def test_zarr_rest_credentials_not_configured(api_client, settings):
    settings.DANDI_ZARR_UPLOAD_ROLE_ARN = None
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create(
        dandiset__owners=[user],
        status=ZarrArchiveStatus.COMPLETE,
        checksum=EMPTY_CHECKSUM,
    )

    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/credentials/')
    assert resp.status_code == 501
    assert resp.json() == ZarrArchive.UPLOAD_CREDENTIALS_UNAVAILABLE_MSG

    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.COMPLETE
