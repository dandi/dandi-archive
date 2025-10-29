from __future__ import annotations

import pytest
import requests
from zarr_checksum.checksum import EMPTY_CHECKSUM

from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.tests.factories import UserFactory
from dandiapi.api.tests.fuzzy import HTTP_URL_RE
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus
from dandiapi.zarr.tests.factories import ZarrArchiveFactory


@pytest.mark.django_db
@pytest.mark.parametrize('embargoed', [False, True])
def test_zarr_rest_upload_start(
    api_client,
    embargoed: bool,  # noqa: FBT001
):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create(
        dandiset__owners=[user],
        dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED
        if embargoed
        else Dandiset.EmbargoStatus.OPEN,
        # Set as complete, to mimic past upload
        status=ZarrArchiveStatus.COMPLETE,
        checksum=EMPTY_CHECKSUM,
        file_count=1,
        size=100,
    )

    resp = api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [{'path': 'foo/bar.txt', 'base64md5': 'DMF1ucDxtqgxw5niaXcmYQ=='}],
    )
    assert resp.status_code == 200
    upload_urls = resp.json()
    assert upload_urls == [HTTP_URL_RE]
    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.PENDING
    assert zarr_archive.checksum is None
    assert zarr_archive.file_count == 0
    assert zarr_archive.size == 0

    upload_extra_headers = {}
    if embargoed:
        upload_extra_headers['x-amz-tagging'] = 'embargoed=true'
    upload_resp = requests.put(
        upload_urls[0],
        data=b'a',
        headers={
            'Content-MD5': 'DMF1ucDxtqgxw5niaXcmYQ==',
            **upload_extra_headers,
        },
    )
    assert upload_resp.status_code == 200
    object_path = zarr_archive.s3_path('foo/bar.txt')
    assert ZarrArchive.storage.exists(object_path)
    tags = ZarrArchive.storage.get_tags(object_path)
    if embargoed:
        assert tags == {'embargoed': 'true'}
    else:
        assert tags == {}


@pytest.mark.django_db
def test_zarr_rest_upload_start_not_an_owner(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create()
    resp = api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [{'path': 'foo/bar.txt', 'base64md5': 'DMF1ucDxtqgxw5niaXcmYQ=='}],
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_rest_finalize(
    api_client,
    zarr_file_factory,
):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create(dandiset__owners=[user])

    # Upload zarr file
    zarr_file_factory(zarr_archive=zarr_archive)

    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    assert resp.status_code == 204

    # Check that zarr ingestion occurred
    zarr_archive.refresh_from_db()
    assert zarr_archive.checksum is not None
    assert zarr_archive.checksum != EMPTY_CHECKSUM
    assert zarr_archive.status == ZarrArchiveStatus.COMPLETE


@pytest.mark.django_db
def test_zarr_rest_finalize_not_an_owner(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create()
    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_rest_finalize_already_ingested(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = ZarrArchiveFactory.create(dandiset__owners=[user])
    api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    assert resp.status_code == 400
