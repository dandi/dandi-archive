from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import IntegrityError
import pytest
from zarr_checksum.checksum import EMPTY_CHECKSUM

from dandiapi.api import tasks
from dandiapi.api.models import Asset, Version
from dandiapi.api.services.publish.exceptions import DandisetZarrsNotCompleteError
from dandiapi.api.tests.factories import DraftVersionFactory, UserFactory
from dandiapi.zarr.models import (
    ZarrArchive,
    ZarrArchiveDandisetPublishingError,
    ZarrArchivePublishedError,
    ZarrArchiveStatus,
)
from dandiapi.zarr.tasks import ingest_zarr_archive
from dandiapi.zarr.tests.factories import ZarrArchiveFactory

if TYPE_CHECKING:
    from rest_framework.test import APIClient


def _publishable_zarr_version(user, draft_asset_factory, zarr_archive_factory, zarr_file_factory):
    """Create a valid draft version containing an ingested zarr asset, ready to publish."""
    draft_version: Version = DraftVersionFactory.create(dandiset__owners=[user])

    zarr_archive: ZarrArchive = zarr_archive_factory(
        dandiset=draft_version.dandiset, status=ZarrArchiveStatus.UPLOADED
    )
    zarr_file_factory(zarr_archive=zarr_archive, path='foo/bar')
    ingest_zarr_archive(zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.COMPLETE

    zarr_asset: Asset = draft_asset_factory(zarr=zarr_archive, blob=None)
    draft_version.assets.add(zarr_asset)

    tasks.validate_asset_metadata_task(zarr_asset.id)
    tasks.validate_version_metadata_task(draft_version.id)
    draft_version.refresh_from_db()
    assert draft_version.publishable

    return draft_version, zarr_archive, zarr_asset


def _published_zarr(**kwargs) -> ZarrArchive:
    return ZarrArchiveFactory.create(
        status=ZarrArchiveStatus.COMPLETE,
        checksum=EMPTY_CHECKSUM,
        published=True,
        **kwargs,
    )


@pytest.mark.django_db
def test_publish_dandiset_with_zarr(
    api_client: APIClient,
    draft_asset_factory,
    zarr_archive_factory,
    zarr_file_factory,
    django_capture_on_commit_callbacks,
):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    draft_version, zarr_archive, zarr_asset = _publishable_zarr_version(
        user, draft_asset_factory, zarr_archive_factory, zarr_file_factory
    )

    with django_capture_on_commit_callbacks(execute=True):
        resp = api_client.post(
            f'/api/dandisets/{draft_version.dandiset.identifier}/versions/draft/publish/'
        )
    assert resp.status_code == 202

    zarr_archive.refresh_from_db()
    zarr_asset.refresh_from_db()
    draft_version.refresh_from_db()
    assert zarr_archive.published
    assert zarr_asset.published
    assert draft_version.status == Version.Status.PUBLISHED

    published_version = draft_version.dandiset.versions.exclude(version='draft').get()
    assert list(published_version.assets.all()) == [zarr_asset]

    resp = api_client.get(f'/api/zarr/{zarr_archive.zarr_id}/')
    assert resp.status_code == 200
    assert resp.json()['published'] is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    'zarr_status',
    [ZarrArchiveStatus.PENDING, ZarrArchiveStatus.UPLOADED, ZarrArchiveStatus.INGESTING],
)
def test_publish_dandiset_with_incomplete_zarr(
    api_client: APIClient,
    draft_asset_factory,
    zarr_archive_factory,
    zarr_file_factory,
    zarr_status,
):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    draft_version, zarr_archive, _ = _publishable_zarr_version(
        user, draft_asset_factory, zarr_archive_factory, zarr_file_factory
    )

    # Mimic the zarr having been modified after its asset was validated
    ZarrArchive.objects.filter(id=zarr_archive.id).update(status=zarr_status, checksum=None)

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/draft/publish/'
    )
    assert resp.status_code == 409
    assert resp.json() == DandisetZarrsNotCompleteError.message

    draft_version.refresh_from_db()
    zarr_archive.refresh_from_db()
    assert draft_version.status == Version.Status.VALID
    assert not zarr_archive.published


@pytest.mark.django_db
def test_publish_dandiset_with_already_published_zarr(
    api_client: APIClient,
    published_asset_factory,
    draft_asset_factory,
    django_capture_on_commit_callbacks,
):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    draft_version: Version = DraftVersionFactory.create(dandiset__owners=[user])

    # A zarr published in a previous version is carried over into the new version untouched
    zarr_archive = _published_zarr(dandiset=draft_version.dandiset)
    zarr_asset: Asset = published_asset_factory(zarr=zarr_archive, blob=None)
    blob_asset: Asset = draft_asset_factory()
    draft_version.assets.add(zarr_asset, blob_asset)
    tasks.validate_asset_metadata_task(blob_asset.id)
    tasks.validate_version_metadata_task(draft_version.id)

    with django_capture_on_commit_callbacks(execute=True):
        resp = api_client.post(
            f'/api/dandisets/{draft_version.dandiset.identifier}/versions/draft/publish/'
        )
    assert resp.status_code == 202

    published_version = draft_version.dandiset.versions.exclude(version='draft').get()
    assert set(published_version.assets.all()) == {zarr_asset, blob_asset}


@pytest.mark.django_db
def test_zarr_published_upload_rejected(api_client: APIClient):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = _published_zarr(dandiset__owners=[user])

    resp = api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [{'path': 'foo/bar.txt', 'base64md5': 'DMF1ucDxtqgxw5niaXcmYQ=='}],
    )
    assert resp.status_code == 400
    assert resp.json() == ZarrArchivePublishedError.message

    zarr_archive.refresh_from_db()
    assert zarr_archive.status == ZarrArchiveStatus.COMPLETE
    assert zarr_archive.checksum == EMPTY_CHECKSUM


@pytest.mark.django_db
def test_zarr_published_delete_files_rejected(api_client: APIClient, zarr_file_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = _published_zarr(dandiset__owners=[user])
    zarr_file = zarr_file_factory(zarr_archive=zarr_archive)

    resp = api_client.delete(
        f'/api/zarr/{zarr_archive.zarr_id}/files/', [{'path': str(zarr_file.path)}]
    )
    assert resp.status_code == 400
    assert resp.json() == ZarrArchivePublishedError.message
    assert zarr_archive.storage.exists(zarr_archive.s3_path(str(zarr_file.path)))


@pytest.mark.django_db
def test_zarr_published_finalize_rejected(api_client: APIClient):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = _published_zarr(dandiset__owners=[user])

    resp = api_client.post(f'/api/zarr/{zarr_archive.zarr_id}/finalize/')
    assert resp.status_code == 400
    assert resp.json() == ZarrArchivePublishedError.message


@pytest.mark.django_db
def test_zarr_published_modification_not_an_owner(api_client: APIClient):
    api_client.force_authenticate(user=UserFactory.create())
    zarr_archive = _published_zarr()

    resp = api_client.post(
        f'/api/zarr/{zarr_archive.zarr_id}/files/',
        [{'path': 'foo/bar.txt', 'base64md5': 'DMF1ucDxtqgxw5niaXcmYQ=='}],
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_zarr_modification_rejected_while_publishing(api_client: APIClient):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    draft_version: Version = DraftVersionFactory.create(
        dandiset__owners=[user], status=Version.Status.PUBLISHING
    )
    zarr_archive = ZarrArchiveFactory.create(dandiset=draft_version.dandiset)
    url = f'/api/zarr/{zarr_archive.zarr_id}'

    resp = api_client.post(
        f'{url}/files/', [{'path': 'foo/bar.txt', 'base64md5': 'DMF1ucDxtqgxw5niaXcmYQ=='}]
    )
    assert resp.status_code == 423
    assert resp.json() == ZarrArchiveDandisetPublishingError.message

    resp = api_client.delete(f'{url}/files/', [{'path': 'foo/bar.txt'}])
    assert resp.status_code == 423

    resp = api_client.post(f'{url}/finalize/')
    assert resp.status_code == 423


@pytest.mark.django_db
@pytest.mark.parametrize('force', [False, True])
def test_ingest_published_zarr_skipped(zarr_file_factory, force: bool):  # noqa: FBT001
    zarr_archive = _published_zarr()
    zarr_file_factory(zarr_archive=zarr_archive)

    ingest_zarr_archive(str(zarr_archive.zarr_id), force=force)

    # Ingestion would have changed these values, had it run
    zarr_archive.refresh_from_db()
    assert zarr_archive.checksum == EMPTY_CHECKSUM
    assert zarr_archive.file_count == 0


@pytest.mark.django_db
def test_zarr_published_mark_pending_rejected():
    zarr_archive = _published_zarr()
    with pytest.raises(ZarrArchivePublishedError):
        zarr_archive.mark_pending()


@pytest.mark.django_db
def test_zarr_published_must_be_complete():
    with pytest.raises(IntegrityError):
        ZarrArchiveFactory.create(published=True, status=ZarrArchiveStatus.PENDING)


@pytest.mark.django_db
def test_zarr_create_same_name_as_published(api_client: APIClient):
    """Re-uploading a published zarr under the same name creates a new zarr archive."""
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    zarr_archive = _published_zarr(dandiset__owners=[user])
    payload = {'name': zarr_archive.name, 'dandiset': zarr_archive.dandiset.identifier}

    resp = api_client.post('/api/zarr/', payload)
    assert resp.status_code == 200
    new_zarr_id = resp.json()['zarr_id']
    assert new_zarr_id != str(zarr_archive.zarr_id)
    assert resp.json()['published'] is False

    # Only one unpublished zarr with a given name may exist
    resp = api_client.post('/api/zarr/', payload)
    assert resp.status_code == 400


@pytest.mark.django_db
def test_zarr_list_filter_published(api_client: APIClient):
    published_zarr = _published_zarr()
    unpublished_zarr = ZarrArchiveFactory.create(
        dandiset=published_zarr.dandiset, name=published_zarr.name
    )
    params = {'dandiset': published_zarr.dandiset.identifier, 'name': published_zarr.name}

    def list_zarr_ids(**extra_params) -> list[str]:
        resp = api_client.get('/api/zarr/', {**params, **extra_params})
        assert resp.status_code == 200
        return [zarr['zarr_id'] for zarr in resp.json()['results']]

    # Without the filter, both zarrs with this name are returned
    assert list_zarr_ids() == [str(published_zarr.zarr_id), str(unpublished_zarr.zarr_id)]
    assert list_zarr_ids(published='false') == [str(unpublished_zarr.zarr_id)]
    assert list_zarr_ids(published='true') == [str(published_zarr.zarr_id)]


@pytest.mark.django_db
def test_replace_published_zarr_and_republish(
    api_client: APIClient,
    draft_asset_factory,
    zarr_archive_factory,
    zarr_file_factory,
    django_capture_on_commit_callbacks,
):
    """
    Exercise the workflow a client must follow to change a zarr which has been published.

    The client detects that the zarr is published, creates a new zarr with the same name, uploads
    to it, and points the existing asset at it. Publishing again must leave the first published
    version referencing the original zarr.
    """
    user = UserFactory.create()
    api_client.force_authenticate(user=user)
    draft_version, old_zarr, old_asset = _publishable_zarr_version(
        user, draft_asset_factory, zarr_archive_factory, zarr_file_factory
    )
    dandiset = draft_version.dandiset
    publish_url = f'/api/dandisets/{dandiset.identifier}/versions/draft/publish/'
    zarr_list_params = {'dandiset': dandiset.identifier, 'name': old_zarr.name}

    with django_capture_on_commit_callbacks(execute=True):
        assert api_client.post(publish_url).status_code == 202

    # The client can tell that the zarr may no longer be modified
    assert api_client.get(f'/api/zarr/{old_zarr.zarr_id}/').json()['published'] is True
    resp = api_client.post(
        f'/api/zarr/{old_zarr.zarr_id}/files/', [{'path': 'foo/bar', 'base64md5': 'x' * 22 + '=='}]
    )
    assert resp.status_code == 400
    assert resp.json() == ZarrArchivePublishedError.message

    # There's no unpublished zarr with this name yet, so one can be created
    assert (
        api_client.get('/api/zarr/', {**zarr_list_params, 'published': 'false'}).json()['results']
        == []
    )
    resp = api_client.post('/api/zarr/', {'name': old_zarr.name, 'dandiset': dandiset.identifier})
    assert resp.status_code == 200
    new_zarr = ZarrArchive.objects.get(zarr_id=resp.json()['zarr_id'])

    # If the client is interrupted here and starts over, creating the zarr again fails, and the
    # existing unpublished zarr is the only one found when filtering by `published`
    resp = api_client.post('/api/zarr/', {'name': old_zarr.name, 'dandiset': dandiset.identifier})
    assert resp.status_code == 400
    results = api_client.get('/api/zarr/', {**zarr_list_params, 'published': 'false'}).json()[
        'results'
    ]
    assert [zarr['zarr_id'] for zarr in results] == [str(new_zarr.zarr_id)]

    # Point the existing asset at the new zarr
    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/versions/draft/assets/{old_asset.asset_id}/',
        {'metadata': old_asset.full_metadata, 'zarr_id': new_zarr.zarr_id},
    )
    assert resp.status_code == 200, resp.json()
    new_asset = Asset.objects.get(asset_id=resp.json()['asset_id'])
    assert new_asset.zarr == new_zarr
    assert list(draft_version.assets.all()) == [new_asset]

    # Upload different content to the new zarr, and ingest it
    zarr_file_factory(zarr_archive=new_zarr, path='foo/baz')
    assert api_client.post(f'/api/zarr/{new_zarr.zarr_id}/finalize/').status_code == 204
    ingest_zarr_archive(new_zarr.zarr_id)
    new_zarr.refresh_from_db()
    assert new_zarr.status == ZarrArchiveStatus.COMPLETE
    assert new_zarr.checksum != old_zarr.checksum

    tasks.validate_asset_metadata_task(new_asset.id)
    tasks.validate_version_metadata_task(draft_version.id)
    with django_capture_on_commit_callbacks(execute=True):
        assert api_client.post(publish_url).status_code == 202

    # Both zarrs are now published, each in its own version, under the same name and path
    old_zarr.refresh_from_db()
    new_zarr.refresh_from_db()
    assert old_zarr.published
    assert new_zarr.published
    first_version, second_version = dandiset.versions.exclude(version='draft').order_by('created')
    assert list(first_version.assets.all()) == [old_asset]
    assert list(second_version.assets.all()) == [new_asset]
    assert old_asset.path == new_asset.path
    assert (
        first_version.assets.get().full_metadata['digest']
        != second_version.assets.get().full_metadata['digest']
    )

    # The cycle can be repeated, with any number of published zarrs sharing the name
    resp = api_client.post('/api/zarr/', {'name': old_zarr.name, 'dandiset': dandiset.identifier})
    assert resp.status_code == 200
    results = api_client.get('/api/zarr/', {**zarr_list_params, 'published': 'false'}).json()[
        'results'
    ]
    assert [zarr['zarr_id'] for zarr in results] == [resp.json()['zarr_id']]
    assert api_client.get('/api/zarr/', zarr_list_params).json()['count'] == 3
