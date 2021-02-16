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
def test_version_rest_update(api_client, user, version):
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)

    new_name = 'A unique and special name!'
    new_metadata = {'foo': 'bar', 'num': 123, 'list': ['a', 'b', 'c']}
    saved_metadata = {
        **new_metadata,
        'name': new_name,
        'identifier': f'DANDI:{version.dandiset.identifier}',
    }

    assert api_client.put(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/',
        {'metadata': new_metadata, 'name': new_name},
        format='json',
    ).data == {
        'dandiset': {
            'identifier': version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'version': version.version,
        'name': new_name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'asset_count': version.asset_count,
        'metadata': saved_metadata,
        'size': version.size,
    }

    version.refresh_from_db()
    assert version.metadata.metadata == saved_metadata
    assert version.metadata.name == new_name


@pytest.mark.django_db
def test_version_rest_update_large(api_client, user, version):
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)

    new_name = 'A unique and special name!'
    new_metadata = {
        'foo': 'bar',
        'num': 123,
        'list': ['a', 'b', 'c'],
        'very_large': 'words' * 10000,
    }
    saved_metadata = {
        **new_metadata,
        'name': new_name,
        'identifier': f'DANDI:{version.dandiset.identifier}',
    }

    assert api_client.put(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/',
        {'metadata': new_metadata, 'name': new_name},
        format='json',
    ).data == {
        'dandiset': {
            'identifier': version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'version': version.version,
        'name': new_name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'asset_count': version.asset_count,
        'metadata': saved_metadata,
        'size': version.size,
    }

    version.refresh_from_db()
    assert version.metadata.metadata == saved_metadata
    assert version.metadata.name == new_name


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
    published_version = Version.objects.get(version=resp.data['version'])
    assert published_version
    assert version.dandiset.versions.count() == 2

    assert version.assets.count() == published_version.assets.count()
    draft_asset = version.assets.first()
    published_asset = published_version.assets.first()
    assert draft_asset.uuid != published_asset.uuid
    assert draft_asset.path == published_asset.path
    assert draft_asset.metadata == published_asset.metadata
    assert draft_asset.blob == published_asset.blob
