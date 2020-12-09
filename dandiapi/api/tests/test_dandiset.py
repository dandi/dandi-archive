from guardian.shortcuts import assign_perm
import pytest

from dandiapi.api.models import Dandiset

from .fuzzy import DANDISET_ID_RE, TIMESTAMP_RE


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
            {'identifier': dandiset.identifier, 'created': TIMESTAMP_RE, 'modified': TIMESTAMP_RE}
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
            {'identifier': dandiset.identifier, 'created': TIMESTAMP_RE, 'modified': TIMESTAMP_RE}
        ],
    }


@pytest.mark.django_db
def test_dandiset_rest_retrieve(api_client, dandiset):
    assert api_client.get(f'/api/dandisets/{dandiset.identifier}/').data == {
        'identifier': dandiset.identifier,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
    }


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
    }
    id = int(response.data['identifier'])

    # Creating a Dandiset has side affects.
    # Verify that the user is the only owner.
    dandiset = Dandiset.objects.get(id=id)
    assert list(dandiset.owners.all()) == [user]
    # Verify that a draft Version and VersionMetadata were also created.
    assert dandiset.versions.count() == 1
    version = dandiset.versions.get()
    assert version.version == 'draft'
    assert version.metadata.name == name
    assert version.metadata.metadata == metadata


@pytest.mark.django_db
def test_dandiset_rest_get_owners(api_client, dandiset, user):
    assign_perm('owner', user, dandiset)

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/users/')

    assert resp.status_code == 200
    assert resp.data == [{'username': user.username}]


@pytest.mark.django_db
def test_dandiset_rest_change_owner(api_client, dandiset, user_factory):
    user1 = user_factory()
    user2 = user_factory()
    assign_perm('owner', user1, dandiset)
    api_client.force_authenticate(user=user1)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': user2.username}],
        format='json',
    )

    assert resp.status_code == 200
    assert resp.data == [{'username': user2.username}]
    assert list(dandiset.owners) == [user2]


@pytest.mark.django_db
def test_dandiset_rest_add_owner(api_client, dandiset, user_factory):
    user1 = user_factory()
    user2 = user_factory()
    assign_perm('owner', user1, dandiset)
    api_client.force_authenticate(user=user1)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': user1.username}, {'username': user2.username}],
        format='json',
    )

    assert resp.status_code == 200
    assert resp.data == [{'username': user1.username}, {'username': user2.username}]
    assert list(dandiset.owners) == [user1, user2]


@pytest.mark.django_db
def test_dandiset_rest_remove_owner(api_client, dandiset, user_factory):
    user1 = user_factory()
    user2 = user_factory()
    assign_perm('owner', user1, dandiset)
    assign_perm('owner', user2, dandiset)
    api_client.force_authenticate(user=user1)

    resp = api_client.put(
        f'/api/dandisets/{dandiset.identifier}/users/',
        [{'username': user1.username}],
        format='json',
    )

    assert resp.status_code == 200
    assert resp.data == [{'username': user1.username}]
    assert list(dandiset.owners) == [user1]


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
