from guardian.shortcuts import assign_perm
import pytest


@pytest.mark.django_db
def test_lock(draft_version, user):
    assign_perm('owner', user, draft_version)
    assert not draft_version.locked
    assert draft_version.locked_by is None

    draft_version.lock(user)

    assert draft_version.locked
    assert draft_version.locked_by == user


@pytest.mark.django_db
def test_lock_twice(draft_version, user):
    assign_perm('owner', user, draft_version)
    draft_version.lock(user)

    with pytest.raises(Exception, match='Draft is locked'):
        draft_version.lock(user)


@pytest.mark.django_db
def test_lock_other_user(draft_version, user_factory):
    user1 = user_factory()
    user2 = user_factory()
    assign_perm('owner', user1, draft_version)
    assign_perm('owner', user2, draft_version)
    draft_version.lock(user1)

    with pytest.raises(Exception, match='Draft is locked'):
        draft_version.lock(user2)


@pytest.mark.django_db
def test_unlock(draft_version, user):
    assign_perm('owner', user, draft_version)
    draft_version.lock(user)

    draft_version.unlock(user)

    assert not draft_version.locked
    assert draft_version.locked_by is None


@pytest.mark.django_db
def test_unlock_unlocked(draft_version, user):
    with pytest.raises(Exception, match='Cannot unlock a draft that is not locked'):
        draft_version.unlock(user)


@pytest.mark.django_db
def test_unlock_other_user(draft_version, user_factory):
    user1 = user_factory()
    user2 = user_factory()
    assign_perm('owner', user1, draft_version)
    assign_perm('owner', user2, draft_version)
    draft_version.lock(user1)

    with pytest.raises(Exception, match='Cannot unlock a draft locked by another user'):
        draft_version.unlock(user2)


# API Tests


@pytest.mark.django_db
def test_lock_rest(api_client, dandiset, user):
    assign_perm('owner', user, dandiset.draft_version)
    api_client.force_authenticate(user=user)

    resp = api_client.post(f'/api/dandisets/{dandiset.identifier}/draft/lock/').data

    assert resp['locked']
    assert resp['locked_by'] == {
        'username': user.username,
    }

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/draft/').data

    assert resp['locked']
    assert resp['locked_by'] == {
        'username': user.username,
    }


@pytest.mark.django_db
def test_lock_rest_not_owner(api_client, dandiset, user):
    api_client.force_authenticate(user=user)

    resp = api_client.post(f'/api/dandisets/{dandiset.identifier}/draft/lock/')

    assert resp.status_code == 403


@pytest.mark.django_db
def test_unlock_rest(api_client, dandiset, user):
    assign_perm('owner', user, dandiset.draft_version)
    dandiset.draft_version.lock(user)
    dandiset.draft_version.save()
    api_client.force_authenticate(user=user)

    resp = api_client.post(f'/api/dandisets/{dandiset.identifier}/draft/unlock/').data

    assert not resp['locked']
    assert resp['locked_by'] is None

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/draft/').data

    assert not resp['locked']
    assert resp['locked_by'] is None
