from guardian.shortcuts import assign_perm
import pytest

from .fuzzy import TIMESTAMP_RE


@pytest.mark.django_db
def test_draft_rest(api_client, draft_version, user):
    assign_perm('owner', user, draft_version)

    resp = api_client.get(f'/api/dandisets/{draft_version.dandiset.identifier}/draft/').data

    assert resp == {
        'dandiset': {
            'identifier': draft_version.dandiset.identifier,
            'created': TIMESTAMP_RE,
            'modified': TIMESTAMP_RE,
        },
        'name': draft_version.name,
        'created': TIMESTAMP_RE,
        'modified': TIMESTAMP_RE,
        'locked': False,
        'locked_by': None,
        'metadata': draft_version.metadata,
        'owners': [{'username': user.username}],
    }


@pytest.mark.django_db
def test_draft_rest_change_owner(api_client, draft_version, user_factory):
    user1 = user_factory()
    user2 = user_factory()
    assign_perm('owner', user1, draft_version)
    api_client.force_authenticate(user=user1)

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}/draft/owners/',
        [{'username': user2.username}],
        format='json',
    )

    assert resp.status_code == 204
    assert list(draft_version.owners) == [user2]


@pytest.mark.django_db
def test_draft_rest_add_owner(api_client, draft_version, user_factory):
    user1 = user_factory()
    user2 = user_factory()
    assign_perm('owner', user1, draft_version)
    api_client.force_authenticate(user=user1)

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}/draft/owners/',
        [{'username': user1.username}, {'username': user2.username}],
        format='json',
    )

    assert resp.status_code == 204
    assert list(draft_version.owners) == [user1, user2]


@pytest.mark.django_db
def test_draft_rest_remove_owner(api_client, draft_version, user_factory):
    user1 = user_factory()
    user2 = user_factory()
    assign_perm('owner', user1, draft_version)
    assign_perm('owner', user2, draft_version)
    api_client.force_authenticate(user=user1)

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}/draft/owners/',
        [{'username': user1.username}],
        format='json',
    )

    assert resp.status_code == 204
    assert list(draft_version.owners) == [user1]


@pytest.mark.django_db
def test_draft_rest_not_an_owner(api_client, draft_version, user):
    api_client.force_authenticate(user=user)

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}/draft/owners/',
        [{'username': user.username}],
        format='json',
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_draft_rest_delete_all_owners_fails(api_client, draft_version, user):
    assign_perm('owner', user, draft_version)
    api_client.force_authenticate(user=user)

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}/draft/owners/',
        [],
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == ['Cannot remove all draft owners']


@pytest.mark.django_db
def test_draft_rest_add_owner_does_not_exist(api_client, draft_version, user):
    assign_perm('owner', user, draft_version)
    api_client.force_authenticate(user=user)
    fake_name = user.username + 'butnotreally'

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}/draft/owners/',
        [{'username': fake_name}],
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == [f'User {fake_name} not found']


@pytest.mark.django_db
def test_draft_rest_add_malformed(api_client, draft_version, user):
    assign_perm('owner', user, draft_version)
    api_client.force_authenticate(user=user)

    resp = api_client.post(
        f'/api/dandisets/{draft_version.dandiset.identifier}/draft/owners/',
        [{'email': user.email}],
        format='json',
    )
    assert resp.status_code == 400
    assert resp.data == [{'username': ['This field is required.']}]
