import hashlib
import os
from pathlib import Path

from guardian.shortcuts import assign_perm
import pytest
from zarr_checksum import compute_zarr_checksum
from zarr_checksum.checksum import EMPTY_CHECKSUM, ZarrDirectoryDigest
from zarr_checksum.generators import ZarrArchiveFile

from dandiapi.api.storage import get_boto_client
from dandiapi.api.tests.fuzzy import HTTP_URL_RE
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus


def uploaded_zarr_files(
    zarr: ZarrArchive, paths: list[str]
) -> tuple[ZarrDirectoryDigest, list[ZarrArchiveFile]]:
    """Upload zarr files and return checksum info."""
    client = get_boto_client(zarr.storage)
    files: list[ZarrArchiveFile] = []
    for path in paths:
        data = os.urandom(100)
        client.put_object(Bucket=zarr.storage.bucket_name, Key=zarr.s3_path(path), Body=data)

        # Create ZarrArchiveFile
        h = hashlib.md5()
        h.update(data)
        files.append(ZarrArchiveFile(path=Path(path), size=100, digest=h.hexdigest()))

    # Compute zarr checksum
    checksum = compute_zarr_checksum(files)
    return [checksum, files]


@pytest.mark.django_db
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
        f'/api/zarr/{zarr_archive.zarr_id}/upload/',
        ['foo/bar.txt'],
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
        f'/api/zarr/{zarr_archive.zarr_id}/upload/',
        ['foo/bar2.txt'],
        format='json',
    )
    assert resp.status_code == 200
    assert resp.json() == [HTTP_URL_RE]


@pytest.mark.django_db
def test_zarr_rest_upload_start_not_an_owner(authenticated_api_client, zarr_archive: ZarrArchive):
    resp = authenticated_api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/upload/',
        ['foo/bar.txt'],
        format='json',
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_rest_finalize(
    authenticated_api_client, user, storage, zarr_archive: ZarrArchive, monkeypatch
):
    assign_perm('owner', user, zarr_archive.dandiset)

    # Pretend like our zarr was defined with the given storage
    monkeypatch.setattr(ZarrArchive, 'storage', storage)

    # Upload zarr files
    checksum, files = uploaded_zarr_files(zarr_archive, ['foo/bar'])

    resp = authenticated_api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/finalize/', {'digest': checksum.digest}
    )
    assert resp.status_code == 204

    # Check that zarr ingestion occured
    zarr_archive.refresh_from_db()
    assert zarr_archive.checksum is not None
    assert zarr_archive.status == ZarrArchiveStatus.COMPLETE


@pytest.mark.django_db
def test_zarr_rest_finalize_mismatch(
    authenticated_api_client, user, storage, zarr_archive: ZarrArchive, monkeypatch
):
    assign_perm('owner', user, zarr_archive.dandiset)

    # Pretend like our zarr was defined with the given storage
    monkeypatch.setattr(ZarrArchive, 'storage', storage)

    # Upload zarr files
    checksum, files = uploaded_zarr_files(zarr_archive, ['foo/bar'])

    # Intentionally provide incorrect digest
    resp = authenticated_api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/finalize/', {'digest': EMPTY_CHECKSUM}
    )
    assert resp.status_code == 204

    # Check that zarr ingestion occured
    zarr_archive.refresh_from_db()
    assert zarr_archive.checksum is not None
    assert zarr_archive.status == ZarrArchiveStatus.MISMATCH
    assert zarr_archive.file_count == 1


@pytest.mark.django_db
def test_zarr_rest_finalize_invalid_digest(
    authenticated_api_client, user, zarr_archive: ZarrArchive, monkeypatch
):
    assign_perm('owner', user, zarr_archive.dandiset)

    # Intentionally provide incorrect digest
    resp = authenticated_api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/finalize/', {'digest': 'asd'}
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_zarr_rest_finalize_not_an_owner(authenticated_api_client, zarr_archive: ZarrArchive):
    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_rest_finalize_already_ingested(
    authenticated_api_client, user, zarr_archive: ZarrArchive
):
    assign_perm('owner', user, zarr_archive.dandiset)
    authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    resp = authenticated_api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    assert resp.status_code == 400
