from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
import pytest
from rest_framework_yaml.renderers import YAMLRenderer

from dandiapi.api.manifests import write_asset_yaml, write_dandiset_yaml
from dandiapi.api.models import AssetBlob, Version


@pytest.mark.django_db
def test_write_dandiset_yaml(storage: Storage, version: Version):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    # tasks.write_manifest_files(version.id)
    write_dandiset_yaml(version)
    expected = YAMLRenderer().render(version.metadata.metadata)

    dandiset_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.yaml'
    )
    with storage.open(dandiset_yaml_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_assets_yaml(storage: Storage, version: Version, asset_factory):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    # Create a new asset in the version so there is information to write
    version.assets.add(asset_factory())

    # tasks.write_manifest_files(version.id)
    write_asset_yaml(version)
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

    # tasks.write_manifest_files(version.id)
    write_dandiset_yaml(version)
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

    # tasks.write_manifest_files(version.id)
    write_asset_yaml(version)
    expected = YAMLRenderer().render([asset.metadata.metadata for asset in version.assets.all()])

    with storage.open(assets_yaml_path) as f:
        assert f.read() == expected
