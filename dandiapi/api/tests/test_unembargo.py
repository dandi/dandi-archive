from __future__ import annotations

from typing import TYPE_CHECKING

import dandischema
from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.models.asset import Asset
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.models.version import Version
from dandiapi.api.services.embargo import (
    AssetBlobEmbargoedError,
    remove_asset_blob_embargoed_tag,
    unembargo_dandiset,
)
from dandiapi.api.services.embargo.exceptions import (
    AssetTagRemovalError,
    DandisetActiveUploadsError,
)
from dandiapi.api.services.embargo.utils import (
    _delete_zarr_object_tags,
    remove_dandiset_embargo_tags,
)
from dandiapi.api.services.exceptions import DandiError
from dandiapi.api.storage import get_boto_client
from dandiapi.api.tasks import unembargo_dandiset_task
from dandiapi.zarr.models import ZarrArchive, ZarrArchiveStatus, zarr_s3_path
from dandiapi.zarr.tasks import ingest_zarr_archive

if TYPE_CHECKING:
    from dandiapi.api.models.asset import AssetBlob


@pytest.mark.django_db
def test_kickoff_dandiset_unembargo_dandiset_not_embargoed(
    api_client, user, dandiset_factory, draft_version_factory
):
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.OPEN)
    draft_version_factory(dandiset=dandiset)
    assign_perm('owner', user, dandiset)
    api_client.force_authenticate(user=user)

    resp = api_client.post(f'/api/dandisets/{dandiset.identifier}/unembargo/')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_kickoff_dandiset_unembargo_not_owner(
    api_client, user, dandiset_factory, draft_version_factory
):
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    draft_version_factory(dandiset=dandiset)
    api_client.force_authenticate(user=user)

    resp = api_client.post(f'/api/dandisets/{dandiset.identifier}/unembargo/')
    assert resp.status_code == 403


@pytest.mark.django_db
def test_kickoff_dandiset_unembargo_active_uploads(
    api_client, user, dandiset_factory, draft_version_factory, upload_factory
):
    dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    draft_version_factory(dandiset=dandiset)
    assign_perm('owner', user, dandiset)
    api_client.force_authenticate(user=user)

    # Test that active uploads prevent unembargp
    upload_factory(dandiset=dandiset)
    resp = api_client.post(f'/api/dandisets/{dandiset.identifier}/unembargo/')
    assert resp.status_code == 400


# transaction=True required due to how `kickoff_dandiset_unembargo` calls `unembargo_dandiset_task`
@pytest.mark.django_db(transaction=True)
def test_kickoff_dandiset_unembargo(api_client, user, draft_version_factory, mailoutbox, mocker):
    draft_version = draft_version_factory(dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    ds: Dandiset = draft_version.dandiset

    assign_perm('owner', user, ds)
    api_client.force_authenticate(user=user)

    # mock this task to check if called
    patched_task = mocker.patch('dandiapi.api.services.embargo.unembargo_dandiset_task')

    resp = api_client.post(f'/api/dandisets/{ds.identifier}/unembargo/')
    assert resp.status_code == 200

    ds.refresh_from_db()
    assert ds.embargo_status == Dandiset.EmbargoStatus.UNEMBARGOING

    # Check that unembargo dandiset task was delayed
    assert len(patched_task.mock_calls) == 1
    assert str(patched_task.mock_calls[0]) == f'call.delay({ds.pk}, {user.id})'


@pytest.mark.django_db
def test_unembargo_dandiset_not_unembargoing(draft_version_factory, user, api_client):
    draft_version = draft_version_factory(dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    ds: Dandiset = draft_version.dandiset

    assign_perm('owner', user, ds)
    api_client.force_authenticate(user=user)

    with pytest.raises(DandiError):
        unembargo_dandiset(ds, user)


@pytest.mark.django_db
def test_unembargo_dandiset_uploads_exist(draft_version_factory, upload_factory, user, api_client):
    draft_version = draft_version_factory(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING
    )
    ds: Dandiset = draft_version.dandiset

    assign_perm('owner', user, ds)
    api_client.force_authenticate(user=user)

    upload_factory(dandiset=ds)
    with pytest.raises(DandisetActiveUploadsError):
        unembargo_dandiset(ds, user)


@pytest.mark.django_db
def test_remove_dandiset_embargo_tags_chunks(
    draft_version_factory,
    asset_factory,
    embargoed_asset_blob_factory,
    mocker,
):
    delete_asset_blob_tags_mock = mocker.patch(
        'dandiapi.api.services.embargo.utils._delete_object_tags'
    )
    chunk_size = mocker.patch('dandiapi.api.services.embargo.utils.TAG_REMOVAL_CHUNK_SIZE', 2)

    draft_version: Version = draft_version_factory(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING
    )
    ds: Dandiset = draft_version.dandiset
    for _ in range(chunk_size + 1):
        asset = asset_factory(blob=embargoed_asset_blob_factory())
        draft_version.assets.add(asset)

    remove_dandiset_embargo_tags(dandiset=ds)

    # Assert that _delete_object_tags was called chunk_size +1 times, to ensure that it works
    # correctly across chunks
    assert len(delete_asset_blob_tags_mock.mock_calls) == chunk_size + 1


@pytest.mark.django_db
def test_remove_dandiset_embargo_tags_fails_remove_tags(
    draft_version_factory,
    asset_factory,
    embargoed_asset_blob_factory,
    mocker,
):
    # Patch function to raise error when called
    mocker.patch('dandiapi.api.services.embargo.utils._delete_object_tags', side_effect=ValueError)

    # Create dandiset/version and add assets
    draft_version: Version = draft_version_factory(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING
    )
    ds: Dandiset = draft_version.dandiset
    for _ in range(2):
        asset = asset_factory(blob=embargoed_asset_blob_factory())
        draft_version.assets.add(asset)

    # Remove tags
    with pytest.raises(AssetTagRemovalError):
        remove_dandiset_embargo_tags(dandiset=ds)


@pytest.mark.django_db
def test_remove_asset_blob_embargoed_tag_fails_on_embargod(embargoed_asset_blob, asset_blob):
    with pytest.raises(AssetBlobEmbargoedError):
        remove_asset_blob_embargoed_tag(embargoed_asset_blob)

    # Test that error not raised on non-embargoed asset blob
    remove_asset_blob_embargoed_tag(asset_blob)


@pytest.mark.django_db
def test_remove_asset_blob_embargoed_tag(asset_blob, mocker):
    mocked_func = mocker.patch('dandiapi.api.services.embargo._delete_object_tags')
    remove_asset_blob_embargoed_tag(asset_blob)
    mocked_func.assert_called_once()


@pytest.mark.django_db
def test_delete_zarr_object_tags_fails_remove_tags(zarr_archive, zarr_file_factory, mocker):
    mocked = mocker.patch(
        'dandiapi.api.services.embargo.utils._delete_object_tags', side_effect=ValueError
    )
    files = [zarr_file_factory(zarr_archive) for _ in range(2)]

    with pytest.raises(AssetTagRemovalError):
        _delete_zarr_object_tags(client=get_boto_client(), zarr=zarr_archive.zarr_id)

    # Check that each file was called 4 times total. Once initially, and 3 retries
    assert mocked.call_count == 4 * len(files)
    for file in files:
        calls = [
            c
            for c in mocked.mock_calls
            if c.kwargs['blob']
            == zarr_s3_path(zarr_id=zarr_archive.zarr_id, zarr_path=str(file.path))
        ]
        assert len(calls) == 4


@pytest.mark.django_db
def test_delete_zarr_object_tags(zarr_archive, zarr_file_factory, mocker):
    mocked_delete_object_tags = mocker.patch(
        'dandiapi.api.services.embargo.utils._delete_object_tags'
    )

    # Create files
    files = [zarr_file_factory(zarr_archive) for _ in range(10)]

    # This should call the mocked function for each file
    _delete_zarr_object_tags(client=get_boto_client(), zarr=zarr_archive.zarr_id)

    assert mocked_delete_object_tags.call_count == len(files)

    called_blobs = sorted([call.kwargs['blob'] for call in mocked_delete_object_tags.mock_calls])
    file_bucket_paths = sorted([zarr_archive.s3_path(str(file.path)) for file in files])
    assert called_blobs == file_bucket_paths


@pytest.mark.django_db
def test_unembargo_dandiset(
    draft_version_factory,
    asset_factory,
    embargoed_asset_blob_factory,
    embargoed_zarr_archive_factory,
    zarr_file_factory,
    mocker,
    mailoutbox,
    user_factory,
):
    draft_version: Version = draft_version_factory(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING
    )
    ds: Dandiset = draft_version.dandiset
    owners = [user_factory() for _ in range(5)]
    for user in owners:
        assign_perm('owner', user, ds)

    embargoed_blob: AssetBlob = embargoed_asset_blob_factory()
    blob_asset = asset_factory(blob=embargoed_blob, status=Asset.Status.VALID)
    draft_version.assets.add(blob_asset)

    zarr_archive: ZarrArchive = embargoed_zarr_archive_factory(
        dandiset=ds, status=ZarrArchiveStatus.UPLOADED
    )
    for _ in range(5):
        zarr_file_factory(zarr_archive)
    ingest_zarr_archive(zarr_id=zarr_archive.zarr_id)
    zarr_archive.refresh_from_db()
    zarr_asset = asset_factory(zarr=zarr_archive, blob=None, status=Asset.Status.VALID)
    draft_version.assets.add(zarr_asset)

    assert all(asset.is_embargoed for asset in draft_version.assets.all())
    assert all(asset.status == Asset.Status.VALID for asset in draft_version.assets.all())

    # Patch this function to check if it's been called, since we can't test the tagging directly
    patched = mocker.patch('dandiapi.api.services.embargo.utils._delete_object_tags')

    unembargo_dandiset(ds, owners[0])

    assert patched.call_count == 1 + zarr_archive.file_count
    assert not any(asset.is_embargoed for asset in draft_version.assets.all())
    assert all(asset.status == Asset.Status.PENDING for asset in draft_version.assets.all())

    ds.refresh_from_db()
    draft_version.refresh_from_db()
    assert ds.embargo_status == Dandiset.EmbargoStatus.OPEN
    assert (
        draft_version.metadata['access'][0]['status']
        == dandischema.models.AccessType.OpenAccess.value
    )

    # Check that a correct email exists
    assert mailoutbox
    assert 'has been unembargoed' in mailoutbox[0].subject
    payload = mailoutbox[0].message().get_payload()[0].get_payload()
    assert ds.identifier in payload
    assert 'has been unembargoed' in payload

    # Check that the email was sent to all owners
    owner_email_set = {user.email for user in owners}
    mailoutbox_to_email_set = set(mailoutbox[0].to)
    assert owner_email_set == mailoutbox_to_email_set


@pytest.mark.django_db
def test_unembargo_dandiset_validate_version_metadata(
    draft_version_factory, asset_factory, user, mocker
):
    from dandiapi.api.services import embargo as embargo_service

    draft_version: Version = draft_version_factory(
        dandiset__embargo_status=Dandiset.EmbargoStatus.UNEMBARGOING
    )
    ds: Dandiset = draft_version.dandiset
    assign_perm('owner', user, ds)

    draft_version.validation_errors = ['error ajhh']
    draft_version.status = Version.Status.INVALID
    draft_version.save()
    draft_version.assets.add(asset_factory())

    # Spy on the imported function in the embargo service
    validate_version_spy = mocker.spy(embargo_service, 'validate_version_metadata')

    unembargo_dandiset(ds, user=user)

    assert validate_version_spy.call_count == 1
    draft_version.refresh_from_db()
    assert not draft_version.validation_errors


@pytest.mark.django_db
def test_unembargo_dandiset_task_failure(draft_version_factory, mailoutbox, user, api_client):
    # Intentionally set the status to embargoed so the task will fail
    draft_version = draft_version_factory(dandiset__embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    ds: Dandiset = draft_version.dandiset

    assign_perm('owner', user, ds)
    api_client.force_authenticate(user=user)

    with pytest.raises(DandiError):
        unembargo_dandiset_task.delay(ds.pk, user.id)

    assert mailoutbox
    assert 'Unembargo failed' in mailoutbox[0].subject
    payload = mailoutbox[0].message().get_payload()[0].get_payload()
    assert ds.identifier in payload
    assert 'error during the unembargo' in payload
