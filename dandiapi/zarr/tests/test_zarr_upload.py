from __future__ import annotations

from guardian.shortcuts import assign_perm
import pytest
from zarr_checksum.checksum import EMPTY_CHECKSUM

from dandiapi.api.tests.fuzzy import HTTP_URL_RE
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus


@pytest.mark.django_db()
def test_zarr_rest_upload_start(
    authenticated_api_client, user, zarr_archive: ZarrArchive, storage, monkeypatch
):
    assign_perm('owner', user, zarr_archive.dandiset)

    # Pretend like our zarr was defined with the given storage
    monkeypatch.setattr(ZarrArchive, 'storage', storage)

    # Set as complete, to mimic past upload
    zarr_archive.status = ZarrArchiveStatus.COMPLETE
    zarr_archive.checksum = EMPTY_CHECKSUM
    zarr_archive.file_count = 1
    zarr_archive.size = 100
    zarr_archive.save()

    # Request upload files
    resp = authenticated_api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [{'path': 'foo/bar.txt', 'base64md5': '12345'}],
        format='json',
    )
    assert resp.status_code == 200
    assert resp.json() == [HTTP_URL_RE]

    # Assert fields updated
    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.PENDING
    assert zarr_archive.checksum is None
    assert zarr_archive.file_count == 0
    assert zarr_archive.size == 0

    # Request more
    resp = authenticated_api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [{'path': 'foo/bar2.txt', 'base64md5': '12345'}],
        format='json',
    )
    assert resp.status_code == 200
    assert resp.json() == [HTTP_URL_RE]


@pytest.mark.django_db()
def test_zarr_rest_upload_start_not_an_owner(authenticated_api_client, zarr_archive: ZarrArchive):
    resp = authenticated_api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [{'path': 'foo/bar.txt', 'base64md5': '12345'}],
        format='json',
    )
    assert resp.status_code == 403


@pytest.mark.django_db()
def test_zarr_rest_finalize(
    authenticated_api_client,
    user,
    storage,
    zarr_archive: ZarrArchive,
    zarr_file_factory,
    monkeypatch,
):
    assign_perm('owner', user, zarr_archive.dandiset)

    # Pretend like our zarr was defined with the given storage
    monkeypatch.setattr(ZarrArchive, 'storage', storage)

    # Upload zarr file
    zarr_file_factory(zarr_archive)

    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    assert resp.status_code == 204

    # Check that zarr ingestion occurred
    zarr_archive.refresh_from_db()
    assert zarr_archive.checksum is not None
    assert zarr_archive.checksum != EMPTY_CHECKSUM
    assert zarr_archive.status == ZarrArchiveStatus.COMPLETE


@pytest.mark.django_db()
def test_zarr_rest_finalize_not_an_owner(authenticated_api_client, zarr_archive: ZarrArchive):
    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    assert resp.status_code == 403


@pytest.mark.django_db()
def test_zarr_rest_finalize_already_ingested(
    authenticated_api_client, user, zarr_archive: ZarrArchive
):
    assign_perm('owner', user, zarr_archive.dandiset)
    authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    assert resp.status_code == 400
