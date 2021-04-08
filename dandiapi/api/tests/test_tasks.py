import hashlib

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
import pytest
from rest_framework_yaml.renderers import YAMLRenderer

from dandiapi.api import tasks
from dandiapi.api.models import AssetBlob, Version


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

    dandiset_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.yaml'
    )
    # TODO this will fail if the test is run twice in the same minute.
    # The same version ID will be generated in the second test,
    # but the dandiset.yaml will still be present from the first test, creating a mismatch.
    # The solution is to remove the file if it already exists in models.Version.write_yamls().
    with storage.open(dandiset_yaml_path) as f:
        assert f.read() == YAMLRenderer().render(version.metadata.metadata)


@pytest.mark.django_db
def test_write_assets_yaml(storage: Storage, version: Version, asset_factory):
    # Pretend like AssetBlob was defined with the given storage
    # The task piggybacks off of the AssetBlob storage to write the yamls
    AssetBlob.blob.field.storage = storage

    # Create a new asset in the version so there is information to write
    version.assets.add(asset_factory())

    tasks.write_yamls(version.id)

    assets_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/assets.yaml'
    )
    with storage.open(assets_yaml_path) as f:
        assert f.read() == YAMLRenderer().render(
            [asset.metadata.metadata for asset in version.assets.all()]
        )


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

    with storage.open(dandiset_yaml_path) as f:
        assert f.read() == YAMLRenderer().render(version.metadata.metadata)


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

    with storage.open(assets_yaml_path) as f:
        assert f.read() == YAMLRenderer().render(
            [asset.metadata.metadata for asset in version.assets.all()]
        )
