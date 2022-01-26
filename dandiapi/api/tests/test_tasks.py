import hashlib

from django.conf import settings
from django.core.files.storage import Storage
import factory
import pytest

from dandiapi.api import tasks
from dandiapi.api.models import Asset, AssetBlob, EmbargoedAssetBlob, Version
from dandiapi.api.models.dandiset import Dandiset


@pytest.mark.django_db
def test_calculate_checksum_task(storage: Storage, asset_blob_factory):
    # Pretend like AssetBlob was defined with the given storage
    AssetBlob.blob.field.storage = storage

    asset_blob = asset_blob_factory(sha256=None)

    h = hashlib.sha256()
    h.update(asset_blob.blob.read())
    sha256 = h.hexdigest()

    tasks.calculate_sha256(asset_blob.blob_id)

    asset_blob.refresh_from_db()

    assert asset_blob.sha256 == sha256


@pytest.mark.django_db
def test_calculate_checksum_task_embargo(storage: Storage, embargoed_asset_blob_factory):
    # Pretend like EmbargoedAssetBlob was defined with the given storage
    EmbargoedAssetBlob.blob.field.storage = storage

    asset_blob = embargoed_asset_blob_factory(sha256=None)

    h = hashlib.sha256()
    h.update(asset_blob.blob.read())
    sha256 = h.hexdigest()

    tasks.calculate_sha256(asset_blob.blob_id)

    asset_blob.refresh_from_db()

    assert asset_blob.sha256 == sha256


@pytest.mark.django_db
def test_write_manifest_files(storage: Storage, version: Version, asset_factory):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    # Create a new asset in the version so there is information to write
    version.assets.add(asset_factory())

    # All of these files should be generated by the task
    assets_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/assets.yaml'
    )
    dandiset_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.yaml'
    )
    assets_jsonld_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/assets.jsonld'
    )
    dandiset_jsonld_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.jsonld'
    )
    collection_jsonld_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/collection.jsonld'
    )

    tasks.write_manifest_files(version.id)

    assert storage.exists(assets_yaml_path)
    assert storage.exists(dandiset_yaml_path)
    assert storage.exists(assets_jsonld_path)
    assert storage.exists(dandiset_jsonld_path)
    assert storage.exists(collection_jsonld_path)


@pytest.mark.django_db
def test_validate_asset_metadata(asset: Asset):
    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.VALID
    assert asset.validation_errors == []


@pytest.mark.django_db
def test_validate_asset_metadata_no_schema_version(asset: Asset):
    asset.metadata = {}
    asset.save()

    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert len(asset.validation_errors) == 1
    assert asset.validation_errors[0]['field'] == ''
    assert asset.validation_errors[0]['message'].startswith('Metadata version None is not allowed.')


@pytest.mark.django_db
def test_validate_asset_metadata_malformed_schema_version(asset: Asset):
    asset.metadata['schemaVersion'] = 'xxx'
    asset.save()

    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert len(asset.validation_errors) == 1
    assert asset.validation_errors[0]['field'] == ''
    assert asset.validation_errors[0]['message'].startswith('Metadata version xxx is not allowed.')


@pytest.mark.django_db
def test_validate_asset_metadata_no_encoding_format(asset: Asset):
    del asset.metadata['encodingFormat']
    asset.save()

    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_errors == [
        {'field': '', 'message': "'encodingFormat' is a required property"}
    ]


@pytest.mark.django_db
def test_validate_asset_metadata_no_digest(asset: Asset):
    asset.blob.sha256 = None
    asset.blob.save()

    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_errors == [
        {'field': 'digest', 'message': 'A non-zarr asset must have a sha2_256.'}
    ]


@pytest.mark.django_db
def test_validate_asset_metadata_malformed_keywords(asset: Asset):
    asset.metadata['keywords'] = 'foo'
    asset.save()

    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_errors == [
        {'field': 'keywords', 'message': "'foo' is not of type 'array'"}
    ]


@pytest.mark.django_db
def test_validate_version_metadata(version: Version, asset: Asset):
    version.assets.add(asset)

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.VALID
    assert version.validation_errors == []


@pytest.mark.django_db
def test_validate_version_metadata_no_schema_version(version: Version, asset: Asset):
    version.assets.add(asset)

    del version.metadata['schemaVersion']
    version.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert len(version.validation_errors) == 1
    assert version.validation_errors[0]['field'] == ''
    assert version.validation_errors[0]['message'].startswith(
        'Metadata version None is not allowed.'
    )


@pytest.mark.django_db
def test_validate_version_metadata_malformed_schema_version(version: Version, asset: Asset):
    version.assets.add(asset)

    version.metadata['schemaVersion'] = 'xxx'
    version.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert len(version.validation_errors) == 1
    assert version.validation_errors[0]['message'].startswith(
        'Metadata version xxx is not allowed.'
    )


@pytest.mark.django_db
def test_validate_version_metadata_no_description(version: Version, asset: Asset):
    version.assets.add(asset)

    del version.metadata['description']
    version.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert version.validation_errors == [
        {'field': '', 'message': "'description' is a required property"}
    ]


@pytest.mark.django_db
def test_validate_version_metadata_malformed_license(version: Version, asset: Asset):
    version.assets.add(asset)

    version.metadata['license'] = 'foo'
    version.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert version.validation_errors == [
        {'field': 'license', 'message': "'foo' is not of type 'array'"}
    ]


@pytest.mark.django_db
def test_unembargo_dandiset(
    dandiset_factory,
    draft_version_factory,
    asset_factory,
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
    draft_version_factory(dandiset=dandiset)

    # Create embargoed assets
    embargoed_asset_blob: EmbargoedAssetBlob = embargoed_asset_blob_factory()
    embargoed_asset: Asset = asset_factory(embargoed_blob=embargoed_asset_blob, blob=None)

    # Assert properties before unembargo
    assert embargoed_asset.embargoed_blob is not None
    assert embargoed_asset.blob is None
    assert embargoed_asset.embargoed_blob.etag != ''

    # Run unembargo
    draft_version = dandiset.draft_version
    draft_version.assets.add(embargoed_asset)
    tasks.unembargo_dandiset(dandiset.pk)
    dandiset.refresh_from_db()
    draft_version.refresh_from_db()

    # Assert correct changes took place
    assert dandiset.embargo_status == Dandiset.EmbargoStatus.OPEN
    assert draft_version.metadata['access'] == 'dandi:OpenAccess'

    asset: Asset = draft_version.assets.first()
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
    draft_version_factory(dandiset=dandiset)

    # Create embargoed assets
    embargoed_asset_blob: EmbargoedAssetBlob = embargoed_asset_blob_factory()
    embargoed_asset: Asset = asset_factory(embargoed_blob=embargoed_asset_blob, blob=None)

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
    draft_version = dandiset.draft_version
    draft_version.assets.add(embargoed_asset)
    tasks.unembargo_dandiset(dandiset.pk)
    dandiset.refresh_from_db()
    draft_version.refresh_from_db()

    # Assert correct changes took place
    assert dandiset.embargo_status == Dandiset.EmbargoStatus.OPEN
    assert draft_version.metadata['access'] == 'dandi:OpenAccess'

    asset: Asset = draft_version.assets.first()
    assert asset.embargoed_blob is None
    assert asset.blob is not None
    assert asset.blob.etag == embargoed_asset_blob.etag
    assert asset.blob == existing_asset_blob
