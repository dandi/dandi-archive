import math

from dandischema.digests.dandietag import PartGenerator, mb, tb
from django.contrib.auth.models import AnonymousUser
import factory
from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api import tasks
from dandiapi.api.models import Asset, AssetBlob, EmbargoedAssetBlob, Version
from dandiapi.api.models.dandiset import Dandiset


@classmethod
def for_file_size(cls, file_size: int) -> PartGenerator:
    if file_size == 0:
        return cls(0, 0, 0)

    # Override default of 64mb
    part_size = mb(6)

    if file_size > tb(5):
        raise ValueError('File is larger than the S3 maximum object size.')

    if math.ceil(file_size / part_size) >= cls.MAX_PARTS:
        part_size = math.ceil(file_size / cls.MAX_PARTS)

    assert cls.MIN_PART_SIZE <= part_size <= cls.MAX_PART_SIZE

    part_qty, final_part_size = divmod(file_size, part_size)
    if final_part_size == 0:
        final_part_size = part_size
    else:
        part_qty += 1
    if part_qty == 1:
        part_size = final_part_size
    return cls(part_qty, part_size, final_part_size)


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
    api_client, dandiset_factory, user_factory, embargo_status, user_status, resp_code
):
    dandiset: Dandiset = dandiset_factory(embargo_status=embargo_status)
    if user_status == 'anonymous':
        user = AnonymousUser
    else:
        user = user_factory()
        api_client.force_authenticate(user=user)
    if user_status == 'owner':
        assign_perm('owner', user, dandiset)

    response = api_client.post(f'/api/dandisets/{dandiset.identifier}/unembargo/')
    assert response.status_code == resp_code


@pytest.mark.django_db
def test_unembargo_dandiset(
    dandiset_factory,
    draft_version_factory,
    asset_factory,
    embargoed_asset_blob_factory,
    storage,
    embargoed_storage,
    monkeypatch,
):
    # Since both fixtures are parametrized, only proceed when they use the same storage backend
    if type(storage) != type(embargoed_storage):
        pytest.skip('Skip tests with mismatched storages')

    # Pretend like AssetBlob/EmbargoedAssetBlob were defined with the given storage
    monkeypatch.setattr(AssetBlob.blob.field, 'storage', storage)
    monkeypatch.setattr(EmbargoedAssetBlob.blob.field, 'storage', embargoed_storage)

    # Monkey patch PartGenerator so that upload and copy use a smaller part size
    monkeypatch.setattr(PartGenerator, 'for_file_size', for_file_size, raising=True)

    # Create dandiset and version
    dandiset: Dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    draft_version: Version = draft_version_factory(dandiset=dandiset)

    # Create an embargoed asset blob that's 10mb in size, to ensure more than one part
    embargoed_asset_blob: EmbargoedAssetBlob = embargoed_asset_blob_factory(size=mb(10))

    # Create asset from embargoed blob
    embargoed_asset: Asset = asset_factory(embargoed_blob=embargoed_asset_blob, blob=None)
    draft_version.assets.add(embargoed_asset)

    # Assert properties before unembargo
    assert embargoed_asset.embargoed_blob is not None
    assert embargoed_asset.blob is None
    assert embargoed_asset.embargoed_blob.etag != ''

    # Run unembargo
    tasks.unembargo_dandiset(dandiset.pk)
    dandiset.refresh_from_db()
    draft_version.refresh_from_db()

    # Assert correct changes took place
    assert dandiset.embargo_status == Dandiset.EmbargoStatus.OPEN
    assert draft_version.metadata['access'] == 'dandi:OpenAccess'

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
    dandiset_factory,
    draft_version_factory,
    asset_factory,
    asset_blob_factory,
    embargoed_asset_blob_factory,
    storage,
    embargoed_storage,
):
    # Since both fixtures are parametrized, only proceed when they use the same storage backend
    if type(storage) != type(embargoed_storage):
        pytest.skip('Skip tests with mismatched storages')

    # Pretend like AssetBlob/EmbargoedAssetBlob were defined with the given storage
    AssetBlob.blob.field.storage = storage
    EmbargoedAssetBlob.blob.field.storage = embargoed_storage

    # Create dandiset and version
    dandiset: Dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    draft_version: Version = draft_version_factory(dandiset=dandiset)

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
    tasks.unembargo_dandiset(dandiset.pk)
    dandiset.refresh_from_db()
    draft_version.refresh_from_db()

    # Assert correct changes took place
    assert dandiset.embargo_status == Dandiset.EmbargoStatus.OPEN
    assert draft_version.metadata['access'] == 'dandi:OpenAccess'

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
    dandiset_factory,
    draft_version_factory,
    asset_factory,
    asset_blob_factory,
    storage,
    embargoed_storage,
):
    # Since both fixtures are parametrized, only proceed when they use the same storage backend
    if type(storage) != type(embargoed_storage):
        pytest.skip('Skip tests with mismatched storages')

    # Pretend like AssetBlob was defined with the given storage
    AssetBlob.blob.field.storage = storage

    # Create dandiset and version
    dandiset: Dandiset = dandiset_factory(embargo_status=Dandiset.EmbargoStatus.EMBARGOED)
    draft_version: Version = draft_version_factory(dandiset=dandiset)

    # Create asset
    asset_blob: AssetBlob = asset_blob_factory()
    asset: Asset = asset_factory(blob=asset_blob, embargoed_blob=None)
    draft_version.assets.add(asset)

    # Assert properties before unembargo
    assert asset.embargoed_blob is None
    assert asset.blob is not None

    # Run unembargo
    tasks.unembargo_dandiset(dandiset.pk)
    dandiset.refresh_from_db()
    draft_version.refresh_from_db()

    # Assert correct changes took place
    assert dandiset.embargo_status == Dandiset.EmbargoStatus.OPEN
    assert draft_version.metadata['access'] == 'dandi:OpenAccess'

    # Assert no new asset created
    fetched_asset: Asset = draft_version.assets.first()
    assert asset == fetched_asset

    # Check that blob is unchanged
    assert fetched_asset.blob == asset_blob
    assert asset.embargoed_blob is None
    assert asset.blob is not None
    assert asset.blob.etag
    assert asset.blob
