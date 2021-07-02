import hashlib

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
import pytest
from rest_framework_yaml.renderers import YAMLRenderer

from dandiapi.api import tasks
from dandiapi.api.models import Asset, AssetBlob, Version


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
def test_write_dandiset_yaml(storage: Storage, version: Version):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    tasks.write_yamls(version.id)
    expected = YAMLRenderer().render(version.metadata.metadata)

    dandiset_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.yaml'
    )
    # TODO this will fail if the test is run twice in the same minute.
    # The same version ID will be generated in the second test,
    # but the dandiset.yaml will still be present from the first test, creating a mismatch.
    # The solution is to remove the file if it already exists in models.Version.write_yamls().
    with storage.open(dandiset_yaml_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_assets_yaml(storage: Storage, version: Version, asset_factory):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    # Create a new asset in the version so there is information to write
    version.assets.add(asset_factory())

    tasks.write_yamls(version.id)
    expected = YAMLRenderer().render([asset.metadata.metadata for asset in version.assets.all()])

    assets_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/assets.yaml'
    )
    with storage.open(assets_yaml_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_dandiset_yaml_already_exists(storage: Storage, version: Version):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    # Save an invalid file for the task to overwrite
    dandiset_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.yaml'
    )
    storage.save(dandiset_yaml_path, ContentFile(b'wrong contents'))

    tasks.write_yamls(version.id)
    expected = YAMLRenderer().render(version.metadata.metadata)

    with storage.open(dandiset_yaml_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_assets_yaml_already_exists(storage: Storage, version: Version, asset_factory):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    # Create a new asset in the version so there is information to write
    version.assets.add(asset_factory())

    # Save an invalid file for the task to overwrite
    assets_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/assets.yaml'
    )
    storage.save(assets_yaml_path, ContentFile(b'wrong contents'))

    tasks.write_yamls(version.id)
    expected = YAMLRenderer().render([asset.metadata.metadata for asset in version.assets.all()])

    with storage.open(assets_yaml_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_validate_asset_metadata(asset: Asset):
    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.VALID
    assert asset.validation_error == ''


@pytest.mark.django_db
def test_validate_asset_metadata_no_schema_version(asset: Asset):
    asset.metadata.metadata = {}
    asset.metadata.save()

    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_error.startswith('Metadata version None is not allowed.')


@pytest.mark.django_db
def test_validate_asset_metadata_malformed_schema_version(asset: Asset):
    asset.metadata.metadata['schemaVersion'] = 'xxx'
    asset.metadata.save()

    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_error.startswith('Metadata version xxx is not allowed.')


@pytest.mark.django_db
def test_validate_asset_metadata_no_encoding_format(asset: Asset):
    del asset.metadata.metadata['encodingFormat']
    asset.metadata.save()

    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_error == (
        '1 validation error for PublishedAsset\n'
        'encodingFormat\n'
        '  field required (type=value_error.missing)'
    )


@pytest.mark.django_db
def test_validate_asset_metadata_no_digest(asset: Asset):
    asset.blob.sha256 = None
    asset.blob.save()

    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_error == (
        '1 validation error for PublishedAsset\n'
        'digest\n'
        '  Digest is missing dandi-etag or sha256 keys. (type=value_error)'
    )


@pytest.mark.django_db
def test_validate_asset_metadata_malformed_keywords(asset: Asset):
    asset.metadata.metadata['keywords'] = 'foo'
    asset.metadata.save()

    tasks.validate_asset_metadata(asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_error == (
        '1 validation error for PublishedAsset\n'
        'keywords\n'
        '  value is not a valid list (type=type_error.list)'
    )


@pytest.mark.skip(reason='https://github.com/dandi/dandi-api/pull/386')
@pytest.mark.django_db
def test_validate_version_metadata(version: Version, asset: Asset):
    version.assets.add(asset)

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.VALID
    assert version.validation_error == ''


@pytest.mark.django_db
def test_validate_version_metadata_no_schema_version(version: Version, asset: Asset):
    version.assets.add(asset)

    del version.metadata.metadata['schemaVersion']
    version.metadata.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert version.validation_error.startswith('Metadata version None is not allowed.')


@pytest.mark.django_db
def test_validate_version_metadata_malformed_schema_version(version: Version, asset: Asset):
    version.assets.add(asset)

    version.metadata.metadata['schemaVersion'] = 'xxx'
    version.metadata.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert version.validation_error.startswith('Metadata version xxx is not allowed.')


@pytest.mark.skip(reason='https://github.com/dandi/dandi-api/pull/386')
@pytest.mark.django_db
def test_validate_version_metadata_no_description(version: Version, asset: Asset):
    version.assets.add(asset)

    del version.metadata.metadata['description']
    version.metadata.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert version.validation_error == (
        '1 validation error for PublishedDandiset\n'
        'description\n'
        '  field required (type=value_error.missing)'
    )


@pytest.mark.skip(reason='https://github.com/dandi/dandi-api/pull/386')
@pytest.mark.django_db
def test_validate_version_metadata_malformed_license(version: Version, asset: Asset):
    version.assets.add(asset)

    version.metadata.metadata['license'] = 'foo'
    version.metadata.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert version.validation_error == (
        '1 validation error for PublishedDandiset\n'
        'license\n'
        '  value is not a valid list (type=type_error.list)'
    )
