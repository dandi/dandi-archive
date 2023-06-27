import math
import os

from dandischema.digests.dandietag import PartGenerator, mb
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
import factory
from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api import tasks
from dandiapi.api.models import Asset, AssetBlob, EmbargoedAssetBlob, Version
from dandiapi.api.models.dandiset import Dandiset
from dandiapi.api.services.embargo import _unembargo_asset, unembargo_dandiset


@pytest.mark.django_db
def test_asset_unembargo(
    embargoed_storage, asset_factory, embargoed_asset_blob_factory, draft_version
):
    # Pretend like EmbargoedAssetBlob was defined with the given storage
    EmbargoedAssetBlob.blob.field.storage = embargoed_storage

    embargoed_asset_blob: EmbargoedAssetBlob = embargoed_asset_blob_factory()
    embargoed_asset: Asset = asset_factory(embargoed_blob=embargoed_asset_blob, blob=None)
    draft_version.assets.add(embargoed_asset)

    # Assert embargoed properties
    embargoed_sha256 = embargoed_asset.sha256
    embargoed_etag = embargoed_asset.embargoed_blob.etag
    assert embargoed_asset.blob is None
    assert embargoed_asset.embargoed_blob is not None
    assert embargoed_asset.sha256 is not None
    assert 'embargo' in embargoed_asset._populate_metadata()['contentUrl'][1]

    # Unembargo
    _unembargo_asset(embargoed_asset)
    asset = embargoed_asset
    asset.refresh_from_db()

    # Assert unembargoed properties
    assert asset.blob is not None
    assert asset.embargoed_blob is None
    assert asset.sha256 == embargoed_sha256
    assert asset.blob.etag == embargoed_etag
    assert 'embargo' not in asset._populate_metadata()['contentUrl'][1]


@pytest.mark.parametrize(
    ('embargo_status', 'user_status', 'resp_code'),
    [
        (Dandiset.EmbargoStatus.OPEN, 'owner', 400),
        (Dandiset.EmbargoStatus.OPEN, 'anonymous', 401),
        (Dandiset.EmbargoStatus.OPEN, 'not-owner', 403),
        (Dandiset.EmbargoStatus.EMBARGOED, 'owner', 200),
        (Dandiset.EmbargoStatus.EMBARGOED, 'anonymous', 401),
        (Dandiset.EmbargoStatus.EMBARGOED, 'not-owner', 403),
        (Dandiset.EmbargoStatus.UNEMBARGOING, 'owner', 400),
        (Dandiset.EmbargoStatus.UNEMBARGOING, 'anonymous', 401),
        (Dandiset.EmbargoStatus.UNEMBARGOING, 'not-owner', 403),
    ],
)
@pytest.mark.django_db
def test_dandiset_rest_unembargo(
    api_client,
    dandiset_factory,
    draft_version_factory,
    user_factory,
    embargo_status,
    user_status,
    resp_code,
):
    dandiset: Dandiset = dandiset_factory(embargo_status=embargo_status)
    draft_version_factory(dandiset=dandiset)

    if user_status == 'anonymous':
        user = AnonymousUser
    else:
        user = user_factory()
        api_client.force_authenticate(user=user)
    if user_status == 'owner':
        assign_perm('owner', user, dandiset)

    response = api_client.post(f'/api/dandisets/{dandiset.identifier}/unembargo/')
    assert response.status_code == resp_code


@pytest.mark.parametrize(
    ('file_size', 'part_size'),
    [
        (100, mb(64)),  # Normal
        (mb(30), mb(5)),  # Few parts
        (mb(100), mb(6)),  # Many parts (tests concurrency)
    ],
)
@pytest.mark.django_db
def test_unembargo_dandiset(
    user,
    dandiset_factory,
    draft_version_factory,
    asset_factory,
    embargoed_asset_blob_factory,
    storage_tuple,
    file_size,
    part_size,
    monkeypatch,
):
    # Pretend like AssetBlob/EmbargoedAssetBlob were defined with the given storage
    storage, embargoed_storage = storage_tuple
    monkeypatch.setattr(AssetBlob.blob.field, 'storage', storage)
    monkeypatch.setattr(EmbargoedAssetBlob.blob.field, 'storage', embargoed_storage)

    # Monkey patch PartGenerator so that upload and copy use a smaller part size
    monkeypatch.setattr(PartGenerator, 'DEFAULT_PART_SIZE', part_size, raising=True)

    # Create dandiset and version
    dandiset: Dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    draft_version: Version = draft_version_factory(dandiset=dandiset)
    assign_perm('owner', user, dandiset)

    # Create an embargoed asset blob
    embargoed_asset_blob: EmbargoedAssetBlob = embargoed_asset_blob_factory(
        size=file_size, blob=SimpleUploadedFile('test', content=os.urandom(file_size))
    )

    # Assert multiple parts were used
    num_parts = math.ceil(file_size / part_size)
    assert embargoed_asset_blob.etag.endswith(f'-{num_parts}')

    # Create asset from embargoed blob
    embargoed_asset: Asset = asset_factory(embargoed_blob=embargoed_asset_blob, blob=None)
    draft_version.assets.add(embargoed_asset)

    # Assert properties before unembargo
    assert embargoed_asset.embargoed_blob is not None
    assert embargoed_asset.blob is None
    assert embargoed_asset.embargoed_blob.etag != ''

    # Run unembargo and validate version metadata
    unembargo_dandiset(user=user, dandiset=dandiset)
    tasks.validate_version_metadata_task(draft_version.pk)
    dandiset.refresh_from_db()
    draft_version.refresh_from_db()

    # Assert correct changes took place
    assert dandiset.embargo_status == Dandiset.EmbargoStatus.OPEN
    assert draft_version.status == Version.Status.VALID
    assert draft_version.metadata['access'] == [
        {'schemaKey': 'AccessRequirements', 'status': 'dandi:OpenAccess'}
    ]

    # Assert no new asset created
    asset: Asset = draft_version.assets.first()
    assert asset == embargoed_asset

    # Check blobs
    assert asset.embargoed_blob is None
    assert asset.blob is not None
    assert asset.blob.etag == embargoed_asset_blob.etag

    blob_id = str(asset.blob.blob_id)
    assert asset.blob.blob.name == f'test-prefix/blobs/{blob_id[:3]}/{blob_id[3:6]}/{blob_id}'


@pytest.mark.django_db
def test_unembargo_dandiset_existing_blobs(
    user,
    dandiset_factory,
    draft_version_factory,
    asset_factory,
    asset_blob_factory,
    embargoed_asset_blob_factory,
    storage_tuple,
):
    # Pretend like AssetBlob/EmbargoedAssetBlob were defined with the given storage
    storage, embargoed_storage = storage_tuple
    AssetBlob.blob.field.storage = storage
    EmbargoedAssetBlob.blob.field.storage = embargoed_storage

    # Create dandiset and version
    dandiset: Dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    draft_version: Version = draft_version_factory(dandiset=dandiset)
    assign_perm('owner', user, dandiset)

    # Create embargoed assets
    embargoed_asset_blob: EmbargoedAssetBlob = embargoed_asset_blob_factory()
    embargoed_asset: Asset = asset_factory(embargoed_blob=embargoed_asset_blob, blob=None)
    draft_version.assets.add(embargoed_asset)

    # Create unembargoed asset with identical data
    embargoed_asset_blob_data = embargoed_asset_blob.blob.read()
    embargoed_asset_blob.blob.seek(0)
    existing_asset_blob = asset_blob_factory(
        blob=factory.django.FileField(data=embargoed_asset_blob_data)
    )

    # Assert properties before unembargo
    assert embargoed_asset.embargoed_blob is not None
    assert embargoed_asset.blob is None
    assert embargoed_asset.embargoed_blob.etag != ''
    assert existing_asset_blob.etag != ''
    assert embargoed_asset_blob.etag == existing_asset_blob.etag

    # Run unembargo
    unembargo_dandiset(user=user, dandiset=dandiset)
    tasks.validate_version_metadata_task(draft_version.pk)
    dandiset.refresh_from_db()
    draft_version.refresh_from_db()

    # Assert correct changes took place
    assert dandiset.embargo_status == Dandiset.EmbargoStatus.OPEN
    assert draft_version.status == Version.Status.VALID
    assert draft_version.metadata['access'] == [
        {'schemaKey': 'AccessRequirements', 'status': 'dandi:OpenAccess'}
    ]

    # Assert no new asset created
    asset: Asset = draft_version.assets.first()
    assert asset == embargoed_asset

    # Check blobs
    assert asset.embargoed_blob is None
    assert asset.blob is not None
    assert asset.blob.etag == embargoed_asset_blob.etag
    assert asset.blob == existing_asset_blob


@pytest.mark.django_db
def test_unembargo_dandiset_normal_asset_blob(
    user,
    dandiset_factory,
    draft_version_factory,
    asset_factory,
    asset_blob_factory,
    storage,
):
    # Pretend like AssetBlob was defined with the given storage
    AssetBlob.blob.field.storage = storage

    # Create dandiset and version
    dandiset: Dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    draft_version: Version = draft_version_factory(dandiset=dandiset)
    assign_perm('owner', user, dandiset)

    # Create asset
    asset_blob: AssetBlob = asset_blob_factory()
    asset: Asset = asset_factory(blob=asset_blob, embargoed_blob=None)
    draft_version.assets.add(asset)

    # Assert properties before unembargo
    assert asset.embargoed_blob is None
    assert asset.blob is not None

    # Run unembargo
    unembargo_dandiset(user=user, dandiset=dandiset)
    tasks.validate_version_metadata_task(draft_version.pk)
    dandiset.refresh_from_db()
    draft_version.refresh_from_db()

    # Assert correct changes took place
    assert dandiset.embargo_status == Dandiset.EmbargoStatus.OPEN
    assert draft_version.status == Version.Status.VALID
    assert draft_version.metadata['access'] == [
        {'schemaKey': 'AccessRequirements', 'status': 'dandi:OpenAccess'}
    ]

    # Assert no new asset created
    fetched_asset: Asset = draft_version.assets.first()
    assert asset == fetched_asset

    # Check that blob is unchanged
    assert fetched_asset.blob == asset_blob
    assert asset.embargoed_blob is None
    assert asset.blob is not None
    assert asset.blob.etag
    assert asset.blob
