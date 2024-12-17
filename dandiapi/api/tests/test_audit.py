from __future__ import annotations

import base64
import hashlib
from typing import TYPE_CHECKING

import pytest

from dandiapi.api.asset_paths import add_version_asset_paths
from dandiapi.api.models import AuditRecord, Dandiset
from dandiapi.api.services.metadata import validate_asset_metadata, validate_version_metadata
from dandiapi.api.services.permissions.dandiset import add_dandiset_owner
from dandiapi.api.storage import get_boto_client
from dandiapi.zarr.models import ZarrArchive

if TYPE_CHECKING:
    from django.contrib.auth import User

    from dandiapi.api.models.audit import AuditRecordType


def verify_model_properties(rec: AuditRecord, user: User):
    """Assert the correct content of the common AuditRecord fields."""
    assert rec.username == user.username
    assert rec.user_email == user.email
    assert rec.user_fullname == f'{user.first_name} {user.last_name}'


def get_latest_audit_record(*, dandiset: Dandiset, record_type: AuditRecordType):
    """Get the most recent AuditRecord associated with a given Dandiset and record type."""
    record = (
        AuditRecord.objects.filter(dandiset_id=dandiset.id, record_type=record_type)
        .order_by('-timestamp')
        .first()
    )
    assert record is not None

    return record


def create_dandiset(
    api_client,
    *,
    user: User,
    name: str | None = None,
    metadata: dict | None = None,
    embargoed: bool = False,
) -> Dandiset:
    """Create a Dandiset for testing through the REST API."""
    name = name or 'Test Dandiset'
    metadata = metadata or {}

    api_client.force_authenticate(user=user)
    resp = api_client.post(
        f'/api/dandisets/{"?embargo=true" if embargoed else ""}',
        {'name': name, 'metadata': metadata},
        format='json',
    )
    assert resp.status_code == 200

    dandiset_id = int(resp.json()['identifier'])
    return Dandiset.objects.get(pk=dandiset_id)


@pytest.mark.django_db
def test_audit_create_dandiset(api_client, user):
    """Test create_dandiset audit record."""
    # Create a Dandiset with specified name and metadata.
    name = 'Dandiset Extraordinaire'
    metadata = {'foo': 'bar'}
    dandiset = create_dandiset(api_client, user=user, name=name, metadata=metadata)

    # Verify the create_dandiset audit record.
    rec = get_latest_audit_record(dandiset=dandiset, record_type='create_dandiset')
    verify_model_properties(rec, user)
    assert rec.details['embargoed'] is False
    for key, value in metadata.items():
        assert rec.details['metadata'][key] == value
    assert rec.details['metadata']['name'] == name


@pytest.mark.django_db
def test_audit_change_owners(api_client, user_factory, draft_version):
    """Test the change_owners audit record."""
    # Create some users.
    alice = user_factory()
    bob = user_factory()
    charlie = user_factory()

    dandiset = draft_version.dandiset
    add_dandiset_owner(dandiset, alice)

    # Change the owners.
    new_owners = [bob, charlie]
    api_client.force_authenticate(user=alice)
    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': u.username} for u in new_owners],
        format='json',
    )
    assert resp.status_code == 200

    # Verify the change_owners audit record.
    def user_info(u):
        return {
            'username': u.username,
            'email': u.email,
            'name': f'{u.first_name} {u.last_name}',
        }

    rec = get_latest_audit_record(dandiset=dandiset, record_type='change_owners')
    verify_model_properties(rec, alice)
    assert rec.details == {
        'added_owners': [user_info(u) for u in [bob, charlie]],
        'removed_owners': [user_info(u) for u in [alice]],
    }


@pytest.mark.django_db
def test_audit_update_metadata(api_client, draft_version, user):
    # Create a Dandiset.
    dandiset = draft_version.dandiset
    add_dandiset_owner(dandiset, user)

    # Edit its metadata.
    metadata = draft_version.metadata
    metadata['foo'] = 'bar'

    api_client.force_authenticate(user=user)
    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/versions/draft/',
        {
            'name': 'baz',
            'metadata': metadata,
        },
        format='json',
    )
    assert resp.status_code == 200

    # Verify the update_metadata audit record.
    rec = get_latest_audit_record(dandiset=dandiset, record_type='update_metadata')
    verify_model_properties(rec, user)
    metadata = rec.details['metadata']
    assert metadata['name'] == 'baz'
    assert metadata['foo'] == 'bar'


@pytest.mark.django_db
def test_audit_delete_dandiset(api_client, user, draft_version):
    # Create a Dandiset.
    dandiset = draft_version.dandiset
    add_dandiset_owner(dandiset, user)

    # Delete the dandiset.
    api_client.force_authenticate(user=user)
    resp = api_client.delete(f'/api/dandisets/{dandiset.identifier}/')
    assert resp.status_code == 204

    # Verify the delete_dandiset audit record
    rec = get_latest_audit_record(dandiset=dandiset, record_type='delete_dandiset')
    verify_model_properties(rec, user)
    assert rec.details == {}


@pytest.mark.django_db(transaction=True)
def test_audit_unembargo(api_client, user):
    """Test the unembargo audit record."""
    # Create an embargoed Dandiset.
    dandiset = create_dandiset(api_client, user=user, embargoed=True)

    # Verify the create_dandiset record's embargoed field.
    rec = get_latest_audit_record(dandiset=dandiset, record_type='create_dandiset')
    verify_model_properties(rec, user)
    assert rec.details['embargoed'] is True

    # Unembargo the Dandiset.
    resp = api_client.post(f'/api/dandisets/{dandiset.identifier}/unembargo/')
    assert resp.status_code == 200

    # Verify the unembargo_dandiset audit record.
    rec = get_latest_audit_record(dandiset=dandiset, record_type='unembargo_dandiset')
    verify_model_properties(rec, user)
    assert rec.details == {}


@pytest.mark.django_db
def test_audit_add_asset(api_client, user, draft_version, asset_blob_factory):
    # Create a Dandiset.
    dandiset = draft_version.dandiset
    add_dandiset_owner(dandiset, user)

    # Add a new asset.
    blob = asset_blob_factory()
    path = 'foo/bar.txt'
    api_client.force_authenticate(user=user)
    resp = api_client.post(
        f'/api/dandisets/{dandiset.identifier}/versions/draft/assets/',
        {
            'blob_id': str(blob.blob_id),
            'metadata': {
                'path': path,
            },
        },
    )
    assert resp.status_code == 200

    # Verify add_asset audit record.
    rec = get_latest_audit_record(dandiset=dandiset, record_type='add_asset')
    verify_model_properties(rec, user)
    assert rec.details['path'] == path
    assert rec.details['asset_blob_id'] == blob.blob_id


@pytest.mark.django_db
def test_audit_update_asset(
    api_client, user, draft_version, asset_blob_factory, draft_asset_factory
):
    # Create a Dandiset with an asset.
    dandiset = draft_version.dandiset
    add_dandiset_owner(dandiset, user)

    path = 'foo/bar.txt'
    asset = draft_asset_factory(path=path)
    asset.versions.add(draft_version)

    # Replace the asset.
    asset_id = asset.asset_id
    blob = asset_blob_factory()
    api_client.force_authenticate(user=user)
    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset_id}/',
        {
            'blob_id': str(blob.blob_id),
            'metadata': {
                'path': path,
            },
        },
    )
    assert resp.status_code == 200

    # Verify update_asset audit record.
    rec = get_latest_audit_record(dandiset=dandiset, record_type='update_asset')
    verify_model_properties(rec, user)
    assert rec.details['path'] == path
    assert rec.details['asset_blob_id'] == blob.blob_id


@pytest.mark.django_db
def test_audit_remove_asset(
    api_client, user, draft_version, asset_blob_factory, draft_asset_factory
):
    # Create a Dandiset with an asset.
    dandiset = draft_version.dandiset
    add_dandiset_owner(dandiset, user)

    path = 'foo/bar.txt'
    asset = draft_asset_factory(path=path)
    asset.versions.add(draft_version)

    # Delete the asset.
    asset_id = asset.asset_id
    api_client.force_authenticate(user=user)
    resp = api_client.delete(
        f'/api/dandisets/{dandiset.identifier}/versions/draft/assets/{asset_id}/',
    )
    assert resp.status_code == 204

    # Verify remove_asset audit record.
    rec = get_latest_audit_record(dandiset=dandiset, record_type='remove_asset')
    verify_model_properties(rec, user)
    assert rec.details['path'] == path
    assert rec.details['asset_id'] == str(asset_id)


@pytest.mark.django_db(transaction=True)
def test_audit_publish_dandiset(
    api_client, user, dandiset_factory, draft_version_factory, draft_asset_factory
):
    # Create a Dandiset whose draft version has one asset.
    dandiset = dandiset_factory()
    add_dandiset_owner(dandiset, user)
    draft_version = draft_version_factory(dandiset=dandiset)
    draft_asset = draft_asset_factory()
    draft_version.assets.add(draft_asset)
    add_version_asset_paths(draft_version)

    # Validate the asset and then the draft version (to make it publishable
    # through the API).
    validate_asset_metadata(asset=draft_asset)
    validate_version_metadata(version=draft_version)

    # Publish the Dandiset.
    api_client.force_authenticate(user=user)
    resp = api_client.post(
        f'/api/dandisets/{dandiset.identifier}/versions/draft/publish/',
    )
    assert resp.status_code == 202

    # Verify publish_dandiset audit record.
    rec = get_latest_audit_record(dandiset=dandiset, record_type='publish_dandiset')
    verify_model_properties(rec, user)
    assert rec.details['version'] == dandiset.most_recent_published_version.version


@pytest.mark.django_db
def test_audit_zarr_create(api_client, user, draft_version):
    # Create a Dandiset.
    dandiset = draft_version.dandiset
    add_dandiset_owner(dandiset, user)

    # Create a Zarr archive.
    api_client.force_authenticate(user=user)
    resp = api_client.post(
        '/api/zarr/',
        {
            'name': 'Test Zarr',
            'dandiset': dandiset.identifier,
        },
    )
    assert resp.status_code == 200

    # Verify the create_zarr audit record.
    zarr_id = resp.json()['zarr_id']

    rec = get_latest_audit_record(dandiset=dandiset, record_type='create_zarr')
    verify_model_properties(rec, user)
    assert rec.details['name'] == 'Test Zarr'
    assert rec.details['zarr_id'] == zarr_id


@pytest.mark.django_db
def test_audit_upload_zarr_chunks(api_client, user, draft_version, zarr_archive_factory, storage):
    ZarrArchive.storage = storage

    # Create a Dandiset and a Zarr archive.
    dandiset = draft_version.dandiset
    add_dandiset_owner(dandiset, user)
    zarr = zarr_archive_factory(dandiset=dandiset)

    # Request some chunk uploads.
    b64hash = base64.b64encode(hashlib.md5(b'a').hexdigest().encode())
    paths = ['a.txt', 'b.txt', 'c.txt']
    api_client.force_authenticate(user=user)
    resp = api_client.post(
        f'/api/zarr/{zarr.zarr_id}/files/',
        [{'path': path, 'base64md5': b64hash} for path in paths],
    )
    assert resp.status_code == 200

    # Verify the upload_zarr_chunks audit record.
    rec = get_latest_audit_record(dandiset=dandiset, record_type='upload_zarr_chunks')
    verify_model_properties(rec, user)
    assert rec.details['zarr_id'] == zarr.zarr_id
    assert rec.details['paths'] == paths


@pytest.mark.django_db
def test_audit_finalize_zarr(
    api_client, user, draft_version, zarr_archive_factory, storage, settings
):
    ZarrArchive.storage = storage

    # Create a Dandiset and a Zarr archive.
    dandiset = draft_version.dandiset
    add_dandiset_owner(dandiset, user)
    zarr = zarr_archive_factory(dandiset=dandiset)

    # Request some chunk uploads.
    b64hash = base64.b64encode(hashlib.md5(b'a').hexdigest().encode())
    paths = ['a.txt', 'b.txt', 'c.txt']
    api_client.force_authenticate(user=user)
    resp = api_client.post(
        f'/api/zarr/{zarr.zarr_id}/files/',
        [{'path': path, 'base64md5': b64hash} for path in paths],
    )
    assert resp.status_code == 200

    # Upload to the presigned URLs.
    boto = get_boto_client()
    zarr_archive = ZarrArchive.objects.get(zarr_id=zarr.zarr_id)
    for path in paths:
        boto.put_object(
            Bucket=settings.DANDI_DANDISETS_BUCKET_NAME, Key=zarr_archive.s3_path(path), Body=b'a'
        )

    # Finalize the zarr.
    resp = api_client.post(
        f'/api/zarr/{zarr.zarr_id}/finalize/',
    )
    assert resp.status_code == 204

    # Verify the finalize_zarr audit record.
    rec = get_latest_audit_record(dandiset=dandiset, record_type='finalize_zarr')
    verify_model_properties(rec, user)
    assert rec.details['zarr_id'] == zarr.zarr_id


@pytest.mark.django_db
def test_audit_delete_zarr_chunks(
    api_client, user, draft_version, zarr_archive_factory, storage, settings
):
    ZarrArchive.storage = storage

    # Create a Dandiset and a Zarr archive.
    dandiset = draft_version.dandiset
    add_dandiset_owner(dandiset, user)
    zarr = zarr_archive_factory(dandiset=dandiset)

    # Request some chunk uploads.
    b64hash = base64.b64encode(hashlib.md5(b'a').hexdigest().encode())
    paths = ['a.txt', 'b.txt', 'c.txt']
    api_client.force_authenticate(user=user)
    resp = api_client.post(
        f'/api/zarr/{zarr.zarr_id}/files/',
        [{'path': path, 'base64md5': b64hash} for path in paths],
    )
    assert resp.status_code == 200

    # Upload to the presigned URLs.
    boto = get_boto_client()
    zarr_archive = ZarrArchive.objects.get(zarr_id=zarr.zarr_id)
    for path in paths:
        boto.put_object(
            Bucket=settings.DANDI_DANDISETS_BUCKET_NAME, Key=zarr_archive.s3_path(path), Body=b'a'
        )

    # Finalize the zarr.
    resp = api_client.post(
        f'/api/zarr/{zarr.zarr_id}/finalize/',
    )
    assert resp.status_code == 204

    # Delete some zarr chunks.
    deleted = ['b.txt', 'c.txt']
    resp = api_client.delete(
        f'/api/zarr/{zarr.zarr_id}/files/',
        [{'path': path} for path in deleted],
    )
    assert resp.status_code == 204

    # Verify the delete_zarr_chunks audit record.
    rec = get_latest_audit_record(dandiset=dandiset, record_type='delete_zarr_chunks')
    verify_model_properties(rec, user)
    assert rec.details['zarr_id'] == zarr.zarr_id
    assert rec.details['paths'] == deleted
