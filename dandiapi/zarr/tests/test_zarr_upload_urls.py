from __future__ import annotations

import base64
import datetime
import hashlib
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.utils import timezone
from freezegun import freeze_time
import pytest
import requests

from dandiapi.api.tests.factories import UserFactory
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus, ZarrUploadURL
from dandiapi.zarr.tasks import (
    delete_expired_zarr_upload_urls,
    ingest_deferred_zarr_archives,
    ingest_zarr_archive,
)
from dandiapi.zarr.tests.factories import ZarrArchiveFactory

if TYPE_CHECKING:
    from rest_framework.test import APIClient


def _base64md5(content: bytes) -> str:
    return base64.b64encode(hashlib.md5(content).digest()).decode()


def _request_upload_urls(
    api_client: APIClient, zarr_archive: ZarrArchive, files: dict[str, bytes]
) -> dict[str, str]:
    """Request upload URLs for the given files, returning a mapping of path to URL."""
    resp = api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [{'path': path, 'base64md5': _base64md5(content)} for path, content in files.items()],
    )
    assert resp.status_code == 200
    return dict(zip(files, resp.json(), strict=True))


def _upload(url: str, content: bytes) -> None:
    resp = requests.put(url, data=content, headers={'Content-MD5': _base64md5(content)})
    assert resp.status_code == 200


def _finalize(api_client: APIClient, zarr_archive: ZarrArchive) -> None:
    # Ingestion is run synchronously in tests
    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    assert resp.status_code == 204
    zarr_archive.refresh_from_db()


def _expire_upload_urls(zarr_archive: ZarrArchive) -> None:
    # Time can't simply be frozen in the future, as S3 rejects requests with a skewed clock
    zarr_archive.upload_urls.update(expires_at=timezone.now() - datetime.timedelta(seconds=1))


@pytest.fixture
def owner():
    return UserFactory.create()


@pytest.fixture
def owner_client(api_client: APIClient, owner) -> APIClient:
    api_client.force_authenticate(user=owner)
    return api_client


@pytest.fixture
def zarr_archive(owner) -> ZarrArchive:
    return ZarrArchiveFactory.create(dandiset__owners=[owner])


@pytest.mark.django_db
def test_zarr_upload_urls_recorded(owner_client: APIClient, zarr_archive: ZarrArchive):
    expiration: datetime.timedelta = settings.DANDI_ZARR_UPLOAD_URL_EXPIRATION

    with freeze_time():
        urls = _request_upload_urls(owner_client, zarr_archive, {'foo//bar': b'a', '/baz': b'b'})
        expected_expires_at = timezone.now() + expiration

    # Paths are recorded as they'll be listed from S3, and MD5s as they'll appear in ETags
    assert sorted(zarr_archive.upload_urls.values_list('path', 'md5', 'expires_at')) == [
        ('baz', hashlib.md5(b'b').hexdigest(), expected_expires_at),
        ('foo/bar', hashlib.md5(b'a').hexdigest(), expected_expires_at),
    ]

    # The URLs themselves must expire no later than the recorded time
    for url in urls.values():
        assert parse_qs(urlparse(url).query)['X-Amz-Expires'] == [
            str(int(expiration.total_seconds()))
        ]


@pytest.mark.django_db
@pytest.mark.parametrize('base64md5', ['not base64!', base64.b64encode(b'too short').decode()])
def test_zarr_upload_invalid_md5(owner_client: APIClient, zarr_archive: ZarrArchive, base64md5):
    resp = owner_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/files/', [{'path': 'foo', 'base64md5': base64md5}]
    )
    assert resp.status_code == 400
    assert not zarr_archive.upload_urls.exists()


@pytest.mark.django_db
def test_zarr_ingest_all_upload_urls_used(owner_client: APIClient, zarr_archive: ZarrArchive):
    """A well behaved upload is ingested immediately, despite its upload URLs being unexpired."""
    files = {'a/0': b'zero', 'a//1': b'one', '/b': b'two'}
    for path, url in _request_upload_urls(owner_client, zarr_archive, files).items():
        _upload(url, files[path])

    _finalize(owner_client, zarr_archive)
    assert zarr_archive.status == ZarrArchiveStatus.COMPLETE
    assert zarr_archive.file_count == 3


@pytest.mark.django_db
def test_zarr_ingest_deferred_unused_upload_url(owner_client: APIClient, zarr_archive: ZarrArchive):
    urls = _request_upload_urls(owner_client, zarr_archive, {'used': b'a', 'unused': b'b'})
    _upload(urls['used'], b'a')

    # The unused URL could still add a file, so ingestion must wait for it to expire
    _finalize(owner_client, zarr_archive)
    assert zarr_archive.status == ZarrArchiveStatus.UPLOADED
    assert zarr_archive.checksum is None

    # The deferred ingestion task doesn't pick up the zarr until its URLs have expired
    ingest_deferred_zarr_archives()
    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.UPLOADED

    _expire_upload_urls(zarr_archive)
    ingest_deferred_zarr_archives()
    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.COMPLETE
    assert zarr_archive.file_count == 1


@pytest.mark.django_db
def test_zarr_ingest_deferred_superseded_upload_url(
    owner_client: APIClient, zarr_archive: ZarrArchive
):
    first_url = _request_upload_urls(owner_client, zarr_archive, {'foo': b'old'})['foo']
    _upload(first_url, b'old')
    second_url = _request_upload_urls(owner_client, zarr_archive, {'foo': b'new'})['foo']
    _upload(second_url, b'new')

    # The first URL could still be used to revert the file to its old content
    _finalize(owner_client, zarr_archive)
    assert zarr_archive.status == ZarrArchiveStatus.UPLOADED


@pytest.mark.django_db
def test_zarr_ingest_deferred_deleted_file(owner_client: APIClient, zarr_archive: ZarrArchive):
    url = _request_upload_urls(owner_client, zarr_archive, {'foo': b'a', 'bar': b'b'})
    _upload(url['foo'], b'a')
    _upload(url['bar'], b'b')
    resp = owner_client.delete(f'/api/zarr/{zarr_archive.zarr_id}/files/', [{'path': 'foo'}])
    assert resp.status_code == 204

    # The URL could still be used to restore the deleted file
    _finalize(owner_client, zarr_archive)
    assert zarr_archive.status == ZarrArchiveStatus.UPLOADED


@pytest.mark.django_db
def test_zarr_ingest_expired_upload_urls_ignored(
    owner_client: APIClient, zarr_archive: ZarrArchive
):
    _request_upload_urls(owner_client, zarr_archive, {'unused': b'a'})
    _expire_upload_urls(zarr_archive)

    _finalize(owner_client, zarr_archive)
    assert zarr_archive.status == ZarrArchiveStatus.COMPLETE


@pytest.mark.django_db
def test_zarr_force_ingest_deferred_while_pending(
    owner_client: APIClient, zarr_archive: ZarrArchive
):
    """A zarr force ingested mid-upload is returned to PENDING, so the upload can continue."""
    _request_upload_urls(owner_client, zarr_archive, {'unused': b'a'})

    ingest_zarr_archive(str(zarr_archive.zarr_id), force=True)
    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.PENDING


@pytest.mark.django_db
def test_ingest_deferred_zarr_archives_dispatch(mocker):
    delay = mocker.patch('dandiapi.zarr.tasks.ingest_zarr_archive.delay')
    now = timezone.now()

    no_urls = ZarrArchiveFactory.create(status=ZarrArchiveStatus.UPLOADED)
    expired = ZarrArchiveFactory.create(status=ZarrArchiveStatus.UPLOADED)
    ZarrUploadURL.objects.create(
        zarr_archive=expired, path='a', md5='0' * 32, expires_at=now - datetime.timedelta(1)
    )
    active = ZarrArchiveFactory.create(status=ZarrArchiveStatus.UPLOADED)
    ZarrUploadURL.objects.create(
        zarr_archive=active, path='a', md5='0' * 32, expires_at=now - datetime.timedelta(1)
    )
    ZarrUploadURL.objects.create(
        zarr_archive=active, path='b', md5='0' * 32, expires_at=now + datetime.timedelta(1)
    )
    ZarrArchiveFactory.create(status=ZarrArchiveStatus.PENDING)

    ingest_deferred_zarr_archives()

    assert sorted(call.args[0] for call in delay.call_args_list) == sorted(
        [str(no_urls.zarr_id), str(expired.zarr_id)]
    )


@pytest.mark.django_db
def test_delete_expired_zarr_upload_urls():
    zarr_archive = ZarrArchiveFactory.create()
    now = timezone.now()
    ZarrUploadURL.objects.create(
        zarr_archive=zarr_archive, path='a', md5='0' * 32, expires_at=now - datetime.timedelta(1)
    )
    active = ZarrUploadURL.objects.create(
        zarr_archive=zarr_archive, path='b', md5='0' * 32, expires_at=now + datetime.timedelta(1)
    )

    delete_expired_zarr_upload_urls()

    assert list(ZarrUploadURL.objects.all()) == [active]
