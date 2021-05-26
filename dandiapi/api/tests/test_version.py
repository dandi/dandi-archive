from datetime import datetime

from django.contrib.auth.models import User
from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api import tasks
from dandiapi.api.models import Asset, Version

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
def test_version_metadata_citation(version):
    name = version.metadata.metadata['name']
    year = datetime.now().year
    url = f'https://dandiarchive.org/{version.dandiset.identifier}/{version.version}'
    assert version.metadata.metadata['citation'] == f'{name} ({year}). Online: {url}'


@pytest.mark.django_db
def test_version_metadata_citation_no_contributors(version):
    version.metadata.metadata['contributor'] = []
    version.save()

    name = version.metadata.metadata['name']
    year = datetime.now().year
    url = f'https://dandiarchive.org/{version.dandiset.identifier}/{version.version}'
    assert version.metadata.metadata['citation'] == f'{name} ({year}). Online: {url}'


@pytest.mark.django_db
def test_version_metadata_citation_contributor_not_in_citation(version):
    version.metadata.metadata['contributor'] = [
        {'name': 'Jane Doe'},
        {'name': 'John Doe', 'includeInCitation': False},
    ]
    version.save()

    name = version.metadata.metadata['name']
    year = datetime.now().year
    url = f'https://dandiarchive.org/{version.dandiset.identifier}/{version.version}'
    assert version.metadata.metadata['citation'] == f'{name} ({year}). Online: {url}'


@pytest.mark.django_db
def test_version_metadata_citation_contributor(version):
    version.metadata.metadata['contributor'] = [{'name': 'Jane Doe', 'includeInCitation': True}]
    version.save()

    name = version.metadata.metadata['name']
    year = datetime.now().year
    url = f'https://dandiarchive.org/{version.dandiset.identifier}/{version.version}'
    assert version.metadata.metadata['citation'] == f'Jane Doe ({year}) {name}. Online: {url}'


@pytest.mark.django_db
def test_version_metadata_citation_multiple_contributors(version):
    version.metadata.metadata['contributor'] = [
        {'name': 'John Doe', 'includeInCitation': True},
        {'name': 'Jane Doe', 'includeInCitation': True},
    ]
    version.save()

    name = version.metadata.metadata['name']
    year = datetime.now().year
    url = f'https://dandiarchive.org/{version.dandiset.identifier}/{version.version}'
    assert (
        version.metadata.metadata['citation']
        == f'John Doe; Jane Doe ({year}) {name}. Online: {url}'
    )


@pytest.mark.django_db
def test_version_metadata_context(version):
    version.metadata.metadata['schemaVersion'] = '6.6.6'
    version.save()

    assert version.metadata.metadata['@context'] == (
        'https://raw.githubusercontent.com/dandi/schema/master/releases/6.6.6/context.json'
    )


@pytest.mark.django_db
def test_version_valid_with_valid_asset(version, asset):
    version.assets.add(asset)

    version.status = Version.Status.VALID
    version.save()
    asset.status = Asset.Status.VALID
    asset.save()

    assert version.valid


@pytest.mark.django_db
@pytest.mark.parametrize(
    'status',
    [
        Version.Status.PENDING,
        Version.Status.VALIDATING,
        Version.Status.INVALID,
    ],
)
def test_version_invalid(version, status):
    version.status = status
    version.save()

    assert not version.valid


@pytest.mark.django_db
@pytest.mark.parametrize(
    'status',
    [
        Asset.Status.PENDING,
        Asset.Status.VALIDATING,
        Asset.Status.INVALID,
    ],
)
def test_version_valid_with_invalid_asset(version, asset, status):
    version.assets.add(asset)

    version.status = Version.Status.VALID
    version.save()

    asset.status = status
    asset.save()

    assert not version.valid


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
                'status': 'Pending',
            }
        ],
    }


@pytest.mark.django_db
def test_version_rest_retrieve(api_client, version):
    assert (
        api_client.get(
            f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/'
        ).data
        == version.metadata.metadata
    )


@pytest.mark.django_db
def test_version_rest_info(api_client, version):
    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/info/'
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
        'status': 'Pending',
        'validation_error': '',
    }


@pytest.mark.django_db
def test_version_rest_info_with_asset(api_client, version, asset):
    version.assets.add(asset)

    assert api_client.get(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/info/'
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
        'status': 'Pending',
        'validation_error': '',
    }


@pytest.mark.django_db
def test_version_rest_update(api_client, user, draft_version):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    new_name = 'A unique and special name!'
    new_metadata = {'foo': 'bar', 'num': 123, 'list': ['a', 'b', 'c']}
    year = datetime.now().year
    url = f'https://dandiarchive.org/{draft_version.dandiset.identifier}/draft'
    saved_metadata = {
        **new_metadata,
        'name': new_name,
        'identifier': f'DANDI:{draft_version.dandiset.identifier}',
        'id': f'DANDI:{draft_version.dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'citation': f'{new_name} ({year}). Online: {url}',
    }

    assert api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/{draft_version.version}/',
        {'metadata': new_metadata, 'name': new_name},
        format='json',
    ).data == {
        'dandiset': {
            'identifier': draft_version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'version': draft_version.version,
        'name': new_name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'asset_count': draft_version.asset_count,
        'metadata': saved_metadata,
        'size': draft_version.size,
        'status': 'Pending',
        'validation_error': '',
    }

    # The version modified date should be updated
    start_time = draft_version.modified
    draft_version.refresh_from_db()
    end_time = draft_version.modified
    assert start_time < end_time

    assert draft_version.metadata.metadata == saved_metadata
    assert draft_version.metadata.name == new_name


@pytest.mark.django_db
def test_version_rest_update_large(api_client, user, draft_version):
    assign_perm('owner', user, draft_version.dandiset)
    api_client.force_authenticate(user=user)

    new_name = 'A unique and special name!'
    new_metadata = {
        'foo': 'bar',
        'num': 123,
        'list': ['a', 'b', 'c'],
        'very_large': 'words' * 10000,
    }
    year = datetime.now().year
    url = f'https://dandiarchive.org/{draft_version.dandiset.identifier}/draft'
    saved_metadata = {
        **new_metadata,
        'name': new_name,
        'identifier': f'DANDI:{draft_version.dandiset.identifier}',
        'id': f'DANDI:{draft_version.dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'citation': f'{new_name} ({year}). Online: {url}',
    }

    assert api_client.put(
        f'/api/dandisets/{draft_version.dandiset.identifier}/versions/{draft_version.version}/',
        {'metadata': new_metadata, 'name': new_name},
        format='json',
    ).data == {
        'dandiset': {
            'identifier': draft_version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'version': draft_version.version,
        'name': new_name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'asset_count': draft_version.asset_count,
        'metadata': saved_metadata,
        'size': draft_version.size,
        'status': 'Pending',
        'validation_error': '',
    }

    draft_version.refresh_from_db()
    assert draft_version.metadata.metadata == saved_metadata
    assert draft_version.metadata.name == new_name


@pytest.mark.django_db
def test_version_rest_update_published_version(api_client, user, published_version):
    assign_perm('owner', user, published_version.dandiset)
    api_client.force_authenticate(user=user)

    new_name = 'A unique and special name!'
    new_metadata = {'foo': 'bar', 'num': 123, 'list': ['a', 'b', 'c']}

    resp = api_client.put(
        f'/api/dandisets/{published_version.dandiset.identifier}'
        f'/versions/{published_version.version}/',
        {'metadata': new_metadata, 'name': new_name},
        format='json',
    )
    assert resp.status_code == 405
    assert resp.data == 'Only draft versions can be modified.'


@pytest.mark.django_db
def test_version_rest_update_not_an_owner(api_client, user, version):
    api_client.force_authenticate(user=user)

    new_name = 'A unique and special name!'
    new_metadata = {'foo': 'bar', 'num': 123, 'list': ['a', 'b', 'c']}

    assert (
        api_client.put(
            f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/',
            {'metadata': new_metadata, 'name': new_name},
            format='json',
        ).status_code
        == 403
    )


@pytest.mark.django_db
# TODO change admin_user back to a normal user once publish is allowed
def test_version_rest_publish(api_client, admin_user: User, draft_version: Version, asset: Asset):
    assign_perm('owner', admin_user, draft_version.dandiset)
    api_client.force_authenticate(user=admin_user)
    draft_version.assets.add(asset)

    # Validate the metadata to mark the version and asset as `VALID`
    tasks.validate_version_metadata(draft_version.id)
    tasks.validate_asset_metadata(draft_version.id, asset.id)
    draft_version.refresh_from_db()
    assert draft_version.valid

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/publish/'
    )
    assert resp.data == {
        'dandiset': {
            'identifier': draft_version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'version': VERSION_ID_RE,
        'name': draft_version.name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'asset_count': 1,
        'size': draft_version.size,
        'status': 'Pending',
    }
    published_version = Version.objects.get(version=resp.data['version'])
    assert published_version
    assert draft_version.dandiset.versions.count() == 2

    # The original asset should now be in both versions
    assert asset == draft_version.assets.get()
    assert asset == published_version.assets.get()
    assert asset.versions.count() == 2


@pytest.mark.django_db
def test_version_rest_publish_not_an_owner(api_client, user, version, asset):
    api_client.force_authenticate(user=user)
    version.assets.add(asset)

    resp = api_client.post(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/publish/'
    )
    assert resp.status_code == 403


# TODO remove this test once publish is allowed
@pytest.mark.django_db
def test_version_rest_publish_not_an_admin(api_client, user, version, asset):
    assign_perm('owner', user, version.dandiset)
    api_client.force_authenticate(user=user)
    version.assets.add(asset)

    resp = api_client.post(
        f'/api/dandisets/{version.dandiset.identifier}/versions/{version.version}/publish/'
    )
    assert resp.status_code == 403
    assert resp.data == 'Must be an admin to publish'


@pytest.mark.django_db
# TODO change admin_user back to a normal user once publish is allowed
def test_version_rest_publish_not_a_draft(api_client, admin_user, published_version, asset):
    assign_perm('owner', admin_user, published_version.dandiset)
    api_client.force_authenticate(user=admin_user)
    published_version.assets.add(asset)

    resp = api_client.post(
        f'/api/dandisets/{published_version.dandiset.identifier}'
        f'/versions/{published_version.version}/publish/'
    )
    assert resp.status_code == 405


@pytest.mark.django_db
@pytest.mark.parametrize(
    'status',
    [
        Version.Status.PENDING,
        Version.Status.VALIDATING,
        Version.Status.INVALID,
    ],
)
# TODO change admin_user back to a normal user once publish is allowed
def test_version_rest_publish_invalid_metadata(
    api_client, admin_user, draft_version, asset, status
):
    assign_perm('owner', admin_user, draft_version.dandiset)
    api_client.force_authenticate(user=admin_user)
    draft_version.assets.add(asset)

    draft_version.status = status
    draft_version.save()

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}'
        f'/versions/{draft_version.version}/publish/'
    )
    assert resp.status_code == 400
    assert resp.data == 'Dandiset metadata or asset metadata is not valid'
