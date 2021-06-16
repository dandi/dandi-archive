from datetime import datetime

from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.models import Dandiset

from .fuzzy import DANDISET_ID_RE, DANDISET_SCHEMA_ID_RE, TIMESTAMP_RE


@pytest.mark.django_db
def test_dandiset_identifier(dandiset):
    assert int(dandiset.identifier) == dandiset.id


def test_dandiset_identifer_missing(dandiset_factory):
    dandiset = dandiset_factory.build()
    # This should have a sane fallback
    assert dandiset.identifier == ''


@pytest.mark.django_db
def test_dandiset_published_count(
    dandiset_factory, draft_version_factory, published_version_factory
):
    # empty dandiset
    dandiset_factory()
    # dandiset with draft version
    draft_version_factory(dandiset=dandiset_factory())
    # dandiset with published version
    published_version_factory(dandiset=dandiset_factory())

    assert Dandiset.published_count() == 1


@pytest.mark.django_db
def test_dandiset_rest_list(api_client, dandiset):
    assert api_client.get('/api/dandisets/').data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'identifier': dandiset.identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'draft_version': None,
                'most_recent_published_version': None,
            }
        ],
    }


@pytest.mark.django_db
def test_dandiset_versions(
    api_client, dandiset_factory, draft_version_factory, published_version_factory
):
    # Create some dandisets of different kinds.
    #
    # Empty dandiset.
    empty = dandiset_factory()

    # Dandiset with a draft version only.
    draft = draft_version_factory().dandiset

    # Dandiset with a published version only.
    published = published_version_factory().dandiset

    assert api_client.get('/api/dandisets/').data == {
        'count': 3,
        'next': None,
        'previous': None,
        'results': [
            {
                'identifier': empty.identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'draft_version': None,
                'most_recent_published_version': None,
            },
            {
                'identifier': draft.identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'draft_version': {
                    'version': draft.draft_version.version,
                    'name': draft.draft_version.name,
                    'asset_count': draft.draft_version.asset_count,
                    'size': draft.draft_version.size,
                    'status': 'Pending',
                    'created': TIMESTAMP_RE,
                    'modified': TIMESTAMP_RE,
                    'dandiset': {
                        'identifier': draft.identifier,
                        'created': TIMESTAMP_RE,
                        'modified': TIMESTAMP_RE,
                    },
                },
                'most_recent_published_version': None,
            },
            {
                'identifier': published.identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'draft_version': None,
                'most_recent_published_version': {
                    'version': published.most_recent_published_version.version,
                    'name': published.most_recent_published_version.name,
                    'asset_count': published.most_recent_published_version.asset_count,
                    'size': published.most_recent_published_version.size,
                    'status': 'Pending',
                    'created': TIMESTAMP_RE,
                    'modified': TIMESTAMP_RE,
                    'dandiset': {
                        'identifier': published.identifier,
                        'created': TIMESTAMP_RE,
                        'modified': TIMESTAMP_RE,
                    },
                },
            },
        ],
    }


@pytest.mark.django_db
def test_dandiset_rest_list_for_user(api_client, user, dandiset_factory):
    dandiset = dandiset_factory()
    # Create an extra dandiset that should not be included in the response
    dandiset_factory()
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, dandiset)
    assert api_client.get('/api/dandisets/?user=me').data == {
        'count': 1,
        'next': None,
        'previous': None,
        'results': [
            {
                'identifier': dandiset.identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
                'draft_version': None,
                'most_recent_published_version': None,
            }
        ],
    }


@pytest.mark.django_db
def test_dandiset_rest_retrieve(api_client, dandiset):
    assert api_client.get(f'/api/dandisets/{dandiset.identifier}/').data == {
        'identifier': dandiset.identifier,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'draft_version': None,
        'most_recent_published_version': None,
    }


"""

                'most_recent_published_version': {
                    'version': dandiset.most_recent_published_version.version,
                    'name': dandiset.most_recent_published_version.name,
                    'asset_count': dandiset.most_recent_published_version.asset_count,
                    'size': dandiset.most_recent_published_version.size,
                    'metadata': dandiset.most_recent_published_version.metadata,
                },
"""


@pytest.mark.django_db
def test_dandiset_rest_create(api_client, user):
    api_client.force_authenticate(user=user)
    name = 'Test Dandiset'
    metadata = {'foo': 'bar'}

    response = api_client.post(
        '/api/dandisets/', {'name': name, 'metadata': metadata}, format='json'
    )
    assert response.data == {
        'identifier': DANDISET_ID_RE,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'draft_version': {
            'version': 'draft',
            'name': name,
            'asset_count': 0,
            'size': 0,
            'dandiset': {
                'identifier': DANDISET_ID_RE,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
            },
            'status': 'Pending',
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'most_recent_published_version': None,
    }
    id = int(response.data['identifier'])

    # Creating a Dandiset has side affects.
    # Verify that the user is the only owner.
    dandiset = Dandiset.objects.get(id=id)
    assert list(dandiset.owners.all()) == [user]

    # Verify that a draft Version and VersionMetadata were also created.
    assert dandiset.versions.count() == 1
    assert dandiset.most_recent_published_version is None
    assert dandiset.draft_version.version == 'draft'
    assert dandiset.draft_version.metadata.name == name

    # Verify that computed metadata was injected
    year = datetime.now().year
    url = f'https://dandiarchive.org/{dandiset.identifier}/draft'
    assert dandiset.draft_version.metadata.metadata == {
        **metadata,
        'name': name,
        'identifier': DANDISET_SCHEMA_ID_RE,
        'id': f'DANDI:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'citation': f'{name} ({year}). (Version draft) [Data set]. DANDI archive. {url}',
        'assetsSummary': {
            'numberOfBytes': 0,
            'numberOfFiles': 0,
            'dataStandard': [],
            'approach': [],
            'measurementTechnique': [],
            'species': [],
        },
    }


@pytest.mark.django_db
def test_dandiset_rest_create_with_identifier(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    name = 'Test Dandiset'
    identifier = '123456'
    metadata = {'foo': 'bar', 'identifier': f'DANDI:{identifier}'}

    response = api_client.post(
        '/api/dandisets/',
        {'name': name, 'metadata': metadata},
        format='json',
    )
    assert response.data == {
        'identifier': identifier,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'most_recent_published_version': None,
        'draft_version': {
            'version': 'draft',
            'name': name,
            'asset_count': 0,
            'size': 0,
            'dandiset': {
                'identifier': identifier,
                'created': TIMESTAMP_RE,
                'modified': TIMESTAMP_RE,
            },
            'status': 'Pending',
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
    }

    # Creating a Dandiset has side affects.
    # Verify that the user is the only owner.
    dandiset = Dandiset.objects.get(id=identifier)
    assert list(dandiset.owners.all()) == [admin_user]

    # Verify that a draft Version and VersionMetadata were also created.
    assert dandiset.versions.count() == 1
    assert dandiset.most_recent_published_version is None
    assert dandiset.draft_version.version == 'draft'
    assert dandiset.draft_version.metadata.name == name

    # Verify that computed metadata was injected
    year = datetime.now().year
    url = f'https://dandiarchive.org/{dandiset.identifier}/draft'
    assert dandiset.draft_version.metadata.metadata == {
        **metadata,
        'name': name,
        'identifier': f'DANDI:{identifier}',
        'id': f'DANDI:{dandiset.identifier}/draft',
        'version': 'draft',
        'url': url,
        'citation': f'{name} ({year}). (Version draft) [Data set]. DANDI archive. {url}',
        'assetsSummary': {
            'numberOfBytes': 0,
            'numberOfFiles': 0,
            'dataStandard': [],
            'approach': [],
            'measurementTechnique': [],
            'species': [],
        },
    }


@pytest.mark.django_db
def test_dandiset_rest_create_with_duplicate_identifier(api_client, admin_user, dandiset):
    api_client.force_authenticate(user=admin_user)
    name = 'Test Dandiset'
    identifier = dandiset.identifier
    metadata = {'foo': 'bar', 'identifier': f'DANDI:{identifier}'}

    response = api_client.post(
        '/api/dandisets/',
        {'name': name, 'metadata': metadata},
        format='json',
    )
    assert response.status_code == 400
    assert response.data == f'Dandiset {identifier} Already Exists'


@pytest.mark.django_db
def test_dandiset_rest_create_with_invalid_identifier(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    name = 'Test Dandiset'
    identifier = 'abc123'
    metadata = {'foo': 'bar', 'identifier': identifier}

    response = api_client.post(
        '/api/dandisets/',
        {'name': name, 'metadata': metadata},
        format='json',
    )
    assert response.status_code == 400
    assert response.data == f'Invalid Identifier {identifier}'


@pytest.mark.django_db
def test_dandiset_rest_delete(api_client, dandiset, user):
    api_client.force_authenticate(user=user)
    assign_perm('owner', user, dandiset)

    response = api_client.delete(f'/api/dandisets/{dandiset.identifier}/')
    assert response.status_code == 204

    assert not Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_delete_not_an_owner(api_client, dandiset, user):
    api_client.force_authenticate(user=user)

    response = api_client.delete(f'/api/dandisets/{dandiset.identifier}/')
    assert response.status_code == 403

    assert dandiset in Dandiset.objects.all()


@pytest.mark.django_db
def test_dandiset_rest_get_owners(api_client, dandiset, social_account):
    assign_perm('owner', social_account.user, dandiset)

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/users/')

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': social_account.extra_data['login'],
            'name': social_account.extra_data['name'],
        }
    ]


@pytest.mark.django_db
def test_dandiset_rest_get_owners_no_social_account(api_client, dandiset, user):
    assign_perm('owner', user, dandiset)

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/users/')

    assert resp.status_code == 200
    assert resp.data == [{'username': user.username}]


@pytest.mark.django_db
def test_dandiset_rest_change_owner(
    api_client,
    draft_version,
    user_factory,
    social_account_factory,
    mailoutbox,
):
    dandiset = draft_version.dandiset
    user1 = user_factory()
    user2 = user_factory()
    social_account2 = social_account_factory(user=user2)
    assign_perm('owner', user1, dandiset)
    api_client.force_authenticate(user=user1)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': social_account2.extra_data['login']}],
        format='json',
    )

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': social_account2.extra_data['login'],
            'name': social_account2.extra_data['name'],
        }
    ]
    assert list(dandiset.owners) == [user2]

    assert len(mailoutbox) == 2
    assert mailoutbox[0].subject == f'Removed from Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[0].to == [user1.email]
    assert mailoutbox[1].subject == f'Added to Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[1].to == [user2.email]


@pytest.mark.django_db
def test_dandiset_rest_add_owner(
    api_client,
    draft_version,
    user_factory,
    social_account_factory,
    mailoutbox,
):
    dandiset = draft_version.dandiset
    user1 = user_factory()
    user2 = user_factory()
    social_account1 = social_account_factory(user=user1)
    social_account2 = social_account_factory(user=user2)
    assign_perm('owner', user1, dandiset)
    api_client.force_authenticate(user=user1)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [
            {'username': social_account1.extra_data['login']},
            {'username': social_account2.extra_data['login']},
        ],
        format='json',
    )

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': social_account1.extra_data['login'],
            'name': social_account1.extra_data['name'],
        },
        {
            'username': social_account2.extra_data['login'],
            'name': social_account2.extra_data['name'],
        },
    ]
    assert list(dandiset.owners) == [user1, user2]

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == f'Added to Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[0].to == [user2.email]


@pytest.mark.django_db
def test_dandiset_rest_remove_owner(
    api_client,
    draft_version,
    user_factory,
    social_account_factory,
    mailoutbox,
):
    dandiset = draft_version.dandiset
    user1 = user_factory()
    user2 = user_factory()
    social_account1 = social_account_factory(user=user1)
    assign_perm('owner', user1, dandiset)
    assign_perm('owner', user2, dandiset)
    api_client.force_authenticate(user=user1)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': social_account1.extra_data['login']}],
        format='json',
    )

    assert resp.status_code == 200
    assert resp.data == [
        {
            'username': social_account1.extra_data['login'],
            'name': social_account1.extra_data['name'],
        }
    ]
    assert list(dandiset.owners) == [user1]

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == f'Removed from Dandiset "{dandiset.draft_version.name}"'
    assert mailoutbox[0].to == [user2.email]


@pytest.mark.django_db
def test_dandiset_rest_not_an_owner(api_client, dandiset, user):
    api_client.force_authenticate(user=user)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': user.username}],
        format='json',
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_dandiset_rest_delete_all_owners_fails(api_client, dandiset, user):
    assign_perm('owner', user, dandiset)
    api_client.force_authenticate(user=user)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [],
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == ['Cannot remove all draft owners']


@pytest.mark.django_db
def test_dandiset_rest_add_owner_does_not_exist(api_client, dandiset, user):
    assign_perm('owner', user, dandiset)
    api_client.force_authenticate(user=user)
    fake_name = user.username + 'butnotreally'

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': fake_name}],
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == [f'User {fake_name} not found']


@pytest.mark.django_db
def test_dandiset_rest_add_malformed(api_client, dandiset, user):
    assign_perm('owner', user, dandiset)
    api_client.force_authenticate(user=user)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'email': user.email}],
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == [{'username': ['This field is required.']}]


@pytest.mark.django_db
def test_dandiset_rest_search_no_query(api_client):
    assert api_client.get('/api/dandisets/').data['results'] == []


@pytest.mark.django_db
def test_dandiset_rest_search_empty_query(api_client):
    assert api_client.get('/api/dandisets/', {'search': ''}).data['results'] == []


@pytest.mark.django_db
def test_dandiset_rest_search_identifier(api_client, draft_version):
    results = api_client.get('/api/dandisets/', {'search': draft_version.dandiset.identifier}).data[
        'results'
    ]
    assert len(results) == 1
    assert results[0]['identifier'] == draft_version.dandiset.identifier

    assert results[0]['most_recent_published_version'] is None

    assert results[0]['draft_version']['version'] == draft_version.version
    assert results[0]['draft_version']['name'] == draft_version.name
