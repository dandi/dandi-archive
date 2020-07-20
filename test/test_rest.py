from tempfile import NamedTemporaryFile

from django.core.files import File
from fuzzy import Timestamp
import pytest

from publish.models import Asset, Dandiset, Version


@pytest.fixture
@pytest.mark.django_db
def dandiset():
    dandiset = Dandiset(id='000001', draft_folder_id='abc123')
    dandiset.save()
    return dandiset


@pytest.fixture
@pytest.mark.django_db
def version(dandiset):
    version = Version(dandiset=dandiset, metadata={'a': 1, 'b': '2', 'c': ['x', 'y', 'z']})
    version.save()
    return version


@pytest.fixture
@pytest.mark.django_db
def asset(version):
    with NamedTemporaryFile('r+b') as local_stream:
        blob = File(file=local_stream, name='foo/bar.nwb',)
        blob.content_type = 'application/octet-stream'
        asset = Asset(
            version=version,
            path='/foo/bar.nwb',
            size=1337,
            sha256='sha256',
            metadata={'foo': ['bar', 'baz']},
            blob=blob,
        )
        asset.save()
    return asset


@pytest.mark.django_db
def test_dandisets_list(client, dandiset):
    assert client.get('/api/dandisets/').json() == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [{'identifier': '000001', 'created': Timestamp(), 'updated': Timestamp()}],
    }


@pytest.mark.django_db
def test_dandisets_read(client, dandiset):
    assert client.get('/api/dandisets/000001/').json() == {
        'identifier': '000001',
        'created': Timestamp(),
        'updated': Timestamp(),
    }


@pytest.mark.django_db
def test_dandisets_versions_list(client, dandiset, version):
    assert client.get('/api/dandisets/000001/versions/').json() == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'dandiset': {
                    'identifier': dandiset.identifier,
                    'created': Timestamp(),
                    'updated': Timestamp(),
                },
                'version': version.version,
                'created': Timestamp(),
                'updated': Timestamp(),
            }
        ],
    }


@pytest.mark.django_db
def test_dandisets_versions_read(client, dandiset, version, asset):
    assert client.get(f'/api/dandisets/000001/versions/{version.version}/').json() == {
        'dandiset': {
            'identifier': dandiset.identifier,
            'created': Timestamp(),
            'updated': Timestamp(),
        },
        'version': version.version,
        'created': Timestamp(),
        'updated': Timestamp(),
        'metadata': version.metadata,
    }


@pytest.mark.django_db
def test_dandisets_versions_assets_list(client, dandiset, version, asset):
    assert client.get(f'/api/dandisets/000001/versions/{version.version}/assets/').json() == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'version': {
                    'dandiset': {
                        'identifier': dandiset.identifier,
                        'created': Timestamp(),
                        'updated': Timestamp(),
                    },
                    'version': version.version,
                    'created': Timestamp(),
                    'updated': Timestamp(),
                },
                'uuid': str(asset.uuid),
                'path': asset.path,
                'size': asset.size,
                'sha256': asset.sha256,
                'created': Timestamp(),
                'updated': Timestamp(),
            }
        ],
    }


@pytest.mark.django_db
def test_dandisets_versions_assets_read(client, dandiset, version, asset):
    assert client.get(
        f'/api/dandisets/000001/versions/{version.version}/assets/{asset.uuid}/'
    ).json() == {
        'version': {
            'dandiset': {
                'identifier': dandiset.identifier,
                'created': Timestamp(),
                'updated': Timestamp(),
            },
            'version': version.version,
            'created': Timestamp(),
            'updated': Timestamp(),
        },
        'uuid': str(asset.uuid),
        'path': asset.path,
        'size': asset.size,
        'sha256': asset.sha256,
        'created': Timestamp(),
        'updated': Timestamp(),
        'metadata': asset.metadata,
    }
