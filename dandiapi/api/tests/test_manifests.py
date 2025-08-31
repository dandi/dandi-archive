from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import pytest
from rest_framework.renderers import JSONRenderer
from rest_framework_yaml.renderers import YAMLRenderer

from dandiapi.api.manifests import (
    _streaming_file_upload,
    write_assets_jsonld,
    write_assets_yaml,
    write_collection_jsonld,
    write_dandiset_jsonld,
    write_dandiset_yaml,
)
from dandiapi.api.models import Version
from dandiapi.api.models.dandiset import Dandiset

if TYPE_CHECKING:
    from dandiapi.api.models import Version


@pytest.mark.parametrize(
    'embargo_status', [Dandiset.EmbargoStatus.OPEN, Dandiset.EmbargoStatus.EMBARGOED]
)
@pytest.mark.django_db
def test_streaming_file_upload(draft_version_factory, embargo_status):
    version: Version = draft_version_factory(dandiset__embargo_status=embargo_status)
    embargoed = version.dandiset.embargoed
    path = 'foo/bar.txt'

    with _streaming_file_upload(path, embargoed=embargoed) as stream:
        stream.write(b'asdasdasd')

    tags = default_storage.get_tags(path)
    if embargoed:
        assert tags == {'embargoed': 'true'}
    else:
        assert tags == {}


@pytest.mark.django_db
def test_write_dandiset_jsonld(version: Version):
    write_dandiset_jsonld(version)
    expected = JSONRenderer().render(version.metadata)

    dandiset_jsonld_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.jsonld'
    )
    with default_storage.open(dandiset_jsonld_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_assets_jsonld(version: Version, asset_factory):
    # Create a new asset in the version so there is information to write
    version.assets.add(asset_factory())

    write_assets_jsonld(version)
    expected = JSONRenderer().render([asset.full_metadata for asset in version.assets.all()])

    assets_jsonld_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/assets.jsonld'
    )
    with default_storage.open(assets_jsonld_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_collection_jsonld(version: Version, asset):
    version.assets.add(asset)
    asset_metadata = asset.full_metadata

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
    with default_storage.open(collection_jsonld_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_dandiset_yaml(version: Version):
    write_dandiset_yaml(version)
    expected = YAMLRenderer().render(version.metadata)

    dandiset_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.yaml'
    )
    with default_storage.open(dandiset_yaml_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_assets_yaml(version: Version, asset_factory):
    # Create a new asset in the version so there is information to write
    version.assets.add(asset_factory())

    write_assets_yaml(version)
    expected = YAMLRenderer().render([asset.full_metadata for asset in version.assets.all()])

    assets_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/assets.yaml'
    )
    with default_storage.open(assets_yaml_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_dandiset_yaml_already_exists(version: Version):
    # Save an invalid file for the task to overwrite
    dandiset_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.yaml'
    )
    default_storage.save(dandiset_yaml_path, ContentFile(b'wrong contents'))

    write_dandiset_yaml(version)
    expected = YAMLRenderer().render(version.metadata)

    with default_storage.open(dandiset_yaml_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_assets_yaml_already_exists(version: Version, asset_factory):
    # Create a new asset in the version so there is information to write
    version.assets.add(asset_factory())

    # Save an invalid file for the task to overwrite
    assets_yaml_path = (
        f'{settings.DANDI_DANDISETS_BUCKET_PREFIX}'
        f'dandisets/{version.dandiset.identifier}/{version.version}/assets.yaml'
    )
    default_storage.save(assets_yaml_path, ContentFile(b'wrong contents'))

    write_assets_yaml(version)
    expected = YAMLRenderer().render([asset.full_metadata for asset in version.assets.all()])

    with default_storage.open(assets_yaml_path) as f:
        assert f.read() == expected
