import os

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
def test_asset_path(api_client, asset):
    path = os.path.split(asset.path)
    asset_directory = path[: len(path) - 1]
    asset_filename = path[len(path) - 1]

    res = api_client.get(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/paths/',
        {'path_prefix': asset_directory},
    )

    assert asset_filename in res.data


@pytest.mark.django_db
def test_invalid_asset_path(api_client, asset):
    path = os.path.split(asset.path)

    # trailing slashes shouldn't have any effect
    asset_directory = f'invalid_path//{path[: len(path) - 1]}///'

    res = api_client.get(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/paths/',
        {'path_prefix': asset_directory},
    )

    assert res.data == []


@pytest.mark.django_db
def test_asset_path_no_prefix(api_client, asset):
    path = os.path.split(asset.path)

    # remove leading slash and append trailing slash
    root_directory = f'{path[0].replace("/", "")}/'

    # make sure not providing 'path_prefix' defaults to '/'
    res = api_client.get(
        f'/api/dandisets/{asset.version.dandiset.identifier}/'
        f'versions/{asset.version.version}/assets/paths/'
    )

    assert root_directory in res.data
