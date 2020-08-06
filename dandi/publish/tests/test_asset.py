import pytest

from dandi.publish.models import Asset
from .fuzzy import TIMESTAMP_RE


@pytest.mark.django_db
def test_asset_from_girder(version, girder_file, mock_girder_client):
    asset = Asset.from_girder(version, girder_file, mock_girder_client)
    assert asset


@pytest.mark.django_db
def test_asset_rest_list(api_client, asset):
    assert api_client.get(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/'
    ).data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'version': {
                    'dandiset': {
                        'identifier': asset.version.dandiset.identifier,
                        'created': TIMESTAMP_RE,
                        'updated': TIMESTAMP_RE,
                    },
                    'version': asset.version.version,
                    'name': asset.version.name,
                    'description': asset.version.description,
                    'created': TIMESTAMP_RE,
                    'updated': TIMESTAMP_RE,
                    'count': 1,
                },
                'uuid': str(asset.uuid),
                'path': asset.path,
                'size': asset.size,
                'sha256': asset.sha256,
                'created': TIMESTAMP_RE,
                'updated': TIMESTAMP_RE,
                'metadata': asset.metadata,
            }
        ],
    }


@pytest.mark.django_db
def test_asset_rest_retrieve(api_client, asset):
    assert api_client.get(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/{asset.uuid}/'
    ).data == {
        'version': {
            'dandiset': {
                'identifier': asset.version.dandiset.identifier,
                'created': TIMESTAMP_RE,
                'updated': TIMESTAMP_RE,
            },
            'version': asset.version.version,
            'name': asset.version.name,
            'description': asset.version.description,
            'created': TIMESTAMP_RE,
            'updated': TIMESTAMP_RE,
            'count': 1,
        },
        'uuid': str(asset.uuid),
        'path': asset.path,
        'size': asset.size,
        'sha256': asset.sha256,
        'created': TIMESTAMP_RE,
        'updated': TIMESTAMP_RE,
        'metadata': asset.metadata,
    }


@pytest.mark.django_db
def test_asset_path_filter(api_client, asset):
    asset_data = {
        'version': {
            'dandiset': {
                'identifier': asset.version.dandiset.identifier,
                'created': TIMESTAMP_RE,
                'updated': TIMESTAMP_RE,
            },
            'version': asset.version.version,
            'name': asset.version.name,
            'description': asset.version.description,
            'created': TIMESTAMP_RE,
            'updated': TIMESTAMP_RE,
            'count': 1,
        },
        'uuid': str(asset.uuid),
        'path': asset.path,
        'size': asset.size,
        'sha256': asset.sha256,
        'created': TIMESTAMP_RE,
        'updated': TIMESTAMP_RE,
        'metadata': asset.metadata,
    }

    partial_path_assets = api_client.get(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/',
        {'path': asset.path[: int(len(asset.path) / 2)]},
    ).data['results']

    full_path_assets = api_client.get(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/',
        {'path': asset.path},
    ).data['results']

    assert asset_data in partial_path_assets
    assert asset_data in full_path_assets
