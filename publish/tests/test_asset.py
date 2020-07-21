import pytest

from .fuzzy import DandisetIdentifierRe, TimestampRe, VersionRe


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
                        'identifier': DandisetIdentifierRe(),
                        'created': TimestampRe(),
                        'updated': TimestampRe(),
                    },
                    'version': VersionRe(),
                    'created': TimestampRe(),
                    'updated': TimestampRe(),
                    'count': 1,
                },
                'uuid': str(asset.uuid),
                'path': asset.path,
                'size': asset.size,
                'sha256': asset.sha256,
                'created': TimestampRe(),
                'updated': TimestampRe(),
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
                'identifier': DandisetIdentifierRe(),
                'created': TimestampRe(),
                'updated': TimestampRe(),
            },
            'version': VersionRe(),
            'created': TimestampRe(),
            'updated': TimestampRe(),
            'count': 1,
        },
        'uuid': str(asset.uuid),
        'path': asset.path,
        'size': asset.size,
        'sha256': asset.sha256,
        'created': TimestampRe(),
        'updated': TimestampRe(),
        'metadata': asset.metadata,
    }
