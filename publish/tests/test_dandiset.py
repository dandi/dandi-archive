import pytest

from .fuzzy import DandisetIdentifierRe, TimestampRe


@pytest.mark.django_db
def test_dandiset_rest_list(api_client, dandiset):
    assert api_client.get('/api/dandisets/').data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'identifier': DandisetIdentifierRe(),
                'created': TimestampRe(),
                'updated': TimestampRe(),
            }
        ],
    }


@pytest.mark.django_db
def test_dandiset_rest_retrieve(api_client, dandiset):
    assert api_client.get(f'/api/dandisets/{dandiset.identifier}/').data == {
        'identifier': DandisetIdentifierRe(),
        'created': TimestampRe(),
        'updated': TimestampRe(),
    }
