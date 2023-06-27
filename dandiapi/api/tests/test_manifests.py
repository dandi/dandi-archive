from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
import pytest
from rest_framework.renderers import JSONRenderer
from rest_framework_yaml.renderers import YAMLRenderer

from dandiapi.api.manifests import (
    write_assets_jsonld,
    write_assets_yaml,
    write_collection_jsonld,
    write_dandiset_jsonld,
    write_dandiset_yaml,
)
from dandiapi.api.models import AssetBlob, Version


@pytest.mark.django_db
def test_write_dandiset_jsonld(storage: Storage, version: Version):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    write_dandiset_jsonld(version)
    expected = JSONRenderer().render(version.metadata)

    dandiset_jsonld_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.jsonld'
    )
    with storage.open(dandiset_jsonld_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_assets_jsonld(storage: Storage, version: Version, asset_factory):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    # Create a new asset in the version so there is information to write
    version.assets.add(asset_factory())

    write_assets_jsonld(version)
    expected = JSONRenderer().render([asset._populate_metadata() for asset in version.assets.all()])

    assets_jsonld_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/assets.jsonld'
    )
    with storage.open(assets_jsonld_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_collection_jsonld(storage: Storage, version: Version, asset):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    version.assets.add(asset)
    asset_metadata = asset._populate_metadata()

    write_collection_jsonld(version)
    expected = JSONRenderer().render(
        {
            '@context': version.metadata['@context'],
            'id': version.metadata['id'],
            '@type': 'prov:Collection',
            'hasMember': [asset_metadata['id']],
        }
    )

    collection_jsonld_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/collection.jsonld'
    )
    with storage.open(collection_jsonld_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_dandiset_yaml(storage: Storage, version: Version):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    write_dandiset_yaml(version)
    expected = YAMLRenderer().render(version.metadata)

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

    write_assets_yaml(version)
    expected = YAMLRenderer().render([asset._populate_metadata() for asset in version.assets.all()])

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

    write_dandiset_yaml(version)
    expected = YAMLRenderer().render(version.metadata)

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

    write_assets_yaml(version)
    expected = YAMLRenderer().render([asset._populate_metadata() for asset in version.assets.all()])

    with storage.open(assets_yaml_path) as f:
        assert f.read() == expected
