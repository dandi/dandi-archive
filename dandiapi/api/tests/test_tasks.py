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
    expected = YAMLRenderer().render(
        [asset.generate_metadata(version) for asset in version.assets.all()]
    )

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
    expected = YAMLRenderer().render(
        [asset.generate_metadata(version) for asset in version.assets.all()]
    )

    with storage.open(assets_yaml_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_validate_asset_metadata(version: Version, asset: Asset):
    version.assets.add(asset)

    # This is the minimum asset metadata for schema version 0.3.0
    asset.metadata.metadata = {
        'schemaVersion': '0.3.0',
        'encodingFormat': 'application/x-nwb',
    }
    asset.metadata.save()

    tasks.validate_asset_metadata(version.id, asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.VALID
    assert asset.validation_error == ''


@pytest.mark.django_db
def test_validate_asset_metadata_no_schema_version(version: Version, asset: Asset):
    version.assets.add(asset)

    asset.metadata.metadata = {}
    asset.metadata.save()

    tasks.validate_asset_metadata(version.id, asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_error == 'schemaVersion not specified'


@pytest.mark.django_db
def test_validate_asset_metadata_malformed_schema_version(version: Version, asset: Asset):
    version.assets.add(asset)

    asset.metadata.metadata = {
        'schemaVersion': 'xxx',
    }
    asset.metadata.save()

    tasks.validate_asset_metadata(version.id, asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_error == (
        '404 Client Error: Not Found for url: '
        'https://raw.githubusercontent.com/dandi/schema/master/releases/xxx/asset.json'
    )


@pytest.mark.django_db
def test_validate_asset_metadata_no_encoding_format(version: Version, asset: Asset):
    version.assets.add(asset)

    asset.metadata.metadata = {
        'schemaVersion': '0.3.0',
    }
    asset.metadata.save()

    tasks.validate_asset_metadata(version.id, asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_error == "'encodingFormat' is a required property\nSee: metadata"


@pytest.mark.django_db
def test_validate_asset_metadata_no_digest(version: Version, asset: Asset):
    version.assets.add(asset)

    asset.metadata.metadata = {
        'schemaVersion': '0.3.0',
        'encodingFormat': 'application/x-nwb',
    }
    asset.metadata.save()

    asset.blob.sha256 = None
    asset.blob.save()

    tasks.validate_asset_metadata(version.id, asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_error == 'SHA256 checksum not computed'


@pytest.mark.django_db
def test_validate_asset_metadata_malformed_keywords(version: Version, asset: Asset):
    version.assets.add(asset)

    asset.metadata.metadata = {
        'schemaVersion': '0.3.0',
        'encodingFormat': 'application/x-nwb',
        'keywords': 'foo',
    }
    asset.metadata.save()

    tasks.validate_asset_metadata(version.id, asset.id)

    asset.refresh_from_db()

    assert asset.status == Asset.Status.INVALID
    assert asset.validation_error == "'foo' is not of type 'array'\nSee: metadata['keywords']"


@pytest.mark.django_db
def test_validate_version_metadata(version: Version):

    # This is the minimum version metadata for schema version 0.3.0
    version.metadata.metadata = {
        'schemaVersion': '0.3.0',
        'description': 'description',
        'contributor': [{}],
        'license': [],
        # 'encodingFormat': 'application/x-nwb',
    }
    version.metadata.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.VALID
    assert version.validation_error == ''


@pytest.mark.django_db
def test_validate_version_metadata_no_schema_version(version: Version):
    version.metadata.metadata = {}
    version.metadata.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert version.validation_error == 'schemaVersion not specified'


@pytest.mark.django_db
def test_validate_version_metadata_malformed_schema_version(version: Version):
    version.metadata.metadata = {
        'schemaVersion': 'xxx',
    }
    version.metadata.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert version.validation_error == (
        '404 Client Error: Not Found for url: '
        'https://raw.githubusercontent.com/dandi/schema/master/releases/xxx/dandiset.json'
    )


@pytest.mark.django_db
def test_validate_version_metadata_no_description(version: Version):
    version.metadata.metadata = {
        'schemaVersion': '0.3.0',
        'contributor': [{}],
        'license': [],
    }
    version.metadata.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert version.validation_error == "'description' is a required property\nSee: metadata"


@pytest.mark.django_db
def test_validate_version_metadata_malformed_license(version: Version):
    version.metadata.metadata = {
        'schemaVersion': '0.3.0',
        'description': 'description',
        'contributor': [{}],
        'license': 'foo',
    }
    version.metadata.save()

    tasks.validate_version_metadata(version.id)

    version.refresh_from_db()

    assert version.status == Version.Status.INVALID
    assert version.validation_error == "'foo' is not of type 'array'\nSee: metadata['license']"
