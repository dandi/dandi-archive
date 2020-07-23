import pytest

from publish.models import Version
from .fuzzy import DandisetIdentifierRe, TimestampRe, VersionRe


@pytest.mark.django_db
def test_version_make_version_nosave(dandiset):
    # Without saving, the output should be reproducible
    version_str_1 = Version.make_version(dandiset)
    version_str_2 = Version.make_version(dandiset)
    assert version_str_1 == version_str_2


@pytest.mark.django_db
def test_version_make_version_save(mocker, dandiset, version_factory):
    # Given an existing version at the current time, a different one should be allocated
    make_version_spy = mocker.spy(Version, 'make_version')
    version_1 = version_factory(dandiset=dandiset)
    make_version_spy.assert_called_once()

    version_str_2 = Version.make_version(dandiset)
    assert version_1.version != version_str_2


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
                'name': version.name,
                'description': version.description,
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
        'name': version.name,
        'description': version.description,
        'created': TimestampRe(),
        'updated': TimestampRe(),
        'count': 0,
        'metadata': version.metadata,
    }
