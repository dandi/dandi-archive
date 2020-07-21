import pytest

from .fuzzy import DandisetIdentifierRe, TimestampRe, VersionRe


@pytest.mark.django_db
def test_version_rest_list(api_client, version):
    assert api_client.get(f'/api/dandisets/{version.dandiset.identifier}/versions/').data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'dandiset': {
                    'identifier': DandisetIdentifierRe(),
                    'created': TimestampRe(),
                    'updated': TimestampRe(),
                },
                'version': VersionRe(),
                'created': TimestampRe(),
                'updated': TimestampRe(),
                'count': 0,
            }
        ],
    }


@pytest.mark.django_db
def test_version_rest_retrieve(api_client, version):
    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/'
    ).data == {
        'dandiset': {
            'identifier': DandisetIdentifierRe(),
            'created': TimestampRe(),
            'updated': TimestampRe(),
        },
        'version': VersionRe(),
        'created': TimestampRe(),
        'updated': TimestampRe(),
        'count': 0,
        'metadata': version.metadata,
    }
