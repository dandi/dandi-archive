from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.models import Version

from .fuzzy import TIMESTAMP_RE, VERSION_ID_RE


@pytest.mark.django_db
def test_version_make_version_nosave(dandiset):
    # Without saving, the output should be reproducible
    version_str_1 = Version.make_version(dandiset)
    version_str_2 = Version.make_version(dandiset)
    assert version_str_1 == version_str_2
    assert version_str_1 == VERSION_ID_RE


@pytest.mark.django_db
def test_version_make_version_save(mocker, dandiset, published_version_factory):
    # Given an existing version at the current time, a different one should be allocated
    make_version_spy = mocker.spy(Version, 'make_version')
    version_1 = published_version_factory(dandiset=dandiset)
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
                    'identifier': version.dandiset.identifier,
                    'created': TIMESTAMP_RE,
                    'modified': TIMESTAMP_RE,
                },
                'version': version.version,
                'name': version.name,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'asset_count': 0,
                'size': 0,
            }
        ],
    }


@pytest.mark.django_db
def test_version_rest_retrieve(api_client, version):
    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/'
    ).data == {
        'dandiset': {
            'identifier': version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'version': version.version,
        'name': version.name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'asset_count': 0,
        'metadata': version.metadata.metadata,
        'size': version.size,
    }


@pytest.mark.django_db
def test_version_rest_retrieve_with_asset(api_client, version, asset_factory):
    asset_factory(version=version)

    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/'
    ).data == {
        'dandiset': {
            'identifier': version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'version': version.version,
        'name': version.name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'asset_count': 1,
        'metadata': version.metadata.metadata,
        'size': version.size,
    }


@pytest.mark.django_db
def test_version_rest_publish(api_client, user, version, asset_factory):
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)
    asset_factory(version=version)

    resp = api_client.post(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/publish/'
    )
    assert resp.data == {
        'dandiset': {
            'identifier': version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'version': VERSION_ID_RE,
        'name': version.name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'asset_count': 1,
        'size': version.size,
    }
    assert Version.objects.get(version=resp.data['version'])
    assert version.dandiset.versions.count() == 2
