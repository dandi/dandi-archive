import pytest

from .fuzzy import TIMESTAMP_RE


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
