from __future__ import annotations

from typing import TYPE_CHECKING

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
from dandiapi.api.tests.factories import DraftVersionFactory

if TYPE_CHECKING:
    from dandiapi.api.models import Version


@pytest.mark.parametrize(
    'embargo_status', [Dandiset.EmbargoStatus.OPEN, Dandiset.EmbargoStatus.EMBARGOED]
)
@pytest.mark.django_db
def test_streaming_file_upload(embargo_status):
    version: Version = DraftVersionFactory.create(dandiset__embargo_status=embargo_status)
    embargoed = version.dandiset.embargoed
    path = 'foo/bar.txt'

    with _streaming_file_upload(path, embargoed=embargoed) as stream:
        stream.write(b'asdasdasd')

    tags = default_storage.get_tags(path)
    if embargoed:
        assert tags == {'embargoed': 'true'}
    else:
        assert tags == {}


def test_streaming_file_upload_multipart(mocker):
    path = 'foo/multipart.txt'
    put_object = mocker.spy(default_storage.s3_client, 'put_object')
    # Enough to need three parts, the last of which is smaller than the others
    chunk = b'0123456789abcdef' * 1024
    chunk_count = 1100

    with _streaming_file_upload(path, embargoed=False) as stream:
        for _ in range(chunk_count):
            stream.write(chunk)

    put_object.assert_not_called()
    assert default_storage.size(path) == len(chunk) * chunk_count
    assert default_storage.e_tag(path).endswith('-3')
    with default_storage.open(path) as f:
        assert f.read() == chunk * chunk_count


def test_streaming_file_upload_empty():
    path = 'foo/empty.txt'
    default_storage.save(path, ContentFile(b'stale'))

    with _streaming_file_upload(path, embargoed=False):
        pass

    assert default_storage.size(path) == 0


@pytest.mark.parametrize('size', [100, 9 * 1024 * 1024], ids=['single-part', 'multipart'])
def test_streaming_file_upload_error(size):
    path = 'foo/error.txt'
    default_storage.save(path, ContentFile(b'original'))

    def failing_upload():
        with _streaming_file_upload(path, embargoed=True) as stream:
            stream.write(b'a' * size)
            raise RuntimeError('oops')

    with pytest.raises(RuntimeError, match='oops'):
        failing_upload()

    # The existing object must be untouched, and nothing may be left behind
    with default_storage.open(path) as f:
        assert f.read() == b'original'
    assert default_storage.get_tags(path) == {}
    uploads = default_storage.s3_client.list_multipart_uploads(
        Bucket=default_storage.bucket_name, Prefix=path
    )
    assert uploads.get('Uploads', []) == []


@pytest.mark.django_db
def test_write_dandiset_jsonld(version: Version):
    write_dandiset_jsonld(version)
    expected = JSONRenderer().render(version.metadata)

    dandiset_jsonld_path = (
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

    assets_jsonld_path = f'dandisets/{version.dandiset.identifier}/{version.version}/assets.jsonld'
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
        f'dandisets/{version.dandiset.identifier}/{version.version}/collection.jsonld'
    )
    with default_storage.open(collection_jsonld_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_dandiset_yaml(version: Version):
    write_dandiset_yaml(version)
    expected = YAMLRenderer().render(version.metadata)

    dandiset_yaml_path = f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.yaml'
    with default_storage.open(dandiset_yaml_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_assets_yaml(version: Version, asset_factory):
    # Create a new asset in the version so there is information to write
    version.assets.add(asset_factory())

    write_assets_yaml(version)
    expected = YAMLRenderer().render([asset.full_metadata for asset in version.assets.all()])

    assets_yaml_path = f'dandisets/{version.dandiset.identifier}/{version.version}/assets.yaml'
    with default_storage.open(assets_yaml_path) as f:
        assert f.read() == expected


@pytest.mark.django_db
def test_write_dandiset_yaml_already_exists(version: Version):
    # Save an invalid file for the task to overwrite
    dandiset_yaml_path = f'dandisets/{version.dandiset.identifier}/{version.version}/dandiset.yaml'
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
    assets_yaml_path = f'dandisets/{version.dandiset.identifier}/{version.version}/assets.yaml'
    default_storage.save(assets_yaml_path, ContentFile(b'wrong contents'))

    write_assets_yaml(version)
    expected = YAMLRenderer().render([asset.full_metadata for asset in version.assets.all()])

    with default_storage.open(assets_yaml_path) as f:
        assert f.read() == expected
