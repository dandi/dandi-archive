import pytest


@pytest.mark.django_db
def test_lock(draft_version, user):
    assert not draft_version.locked
    assert draft_version.locked_by is None

    draft_version.lock(user)

    assert draft_version.locked
    assert draft_version.locked_by == user


@pytest.mark.django_db
def test_lock_twice(draft_version, user):
    draft_version.lock(user)

    with pytest.raises(Exception, match='Draft is locked'):
        draft_version.lock(user)


@pytest.mark.django_db
def test_lock_other_user(draft_version, user_factory):
    draft_version.lock(user_factory())

    with pytest.raises(Exception, match='Draft is locked'):
        draft_version.lock(user_factory())


@pytest.mark.django_db
def test_unlock(draft_version, user):
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
    draft_version.lock(user_factory())

    with pytest.raises(Exception, match='Cannot unlock a draft locked by another user'):
        draft_version.unlock(user_factory())


# API Tests


@pytest.mark.django_db
def test_lock_rest(api_client, dandiset, user):
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
def test_unlock_rest(api_client, dandiset, user):
    dandiset.draft_version.lock(user)
    dandiset.draft_version.save()
    api_client.force_authenticate(user=user)

    resp = api_client.post(f'/api/dandisets/{dandiset.identifier}/draft/unlock/').data

    assert not resp['locked']
    assert resp['locked_by'] is None

    resp = api_client.get(f'/api/dandisets/{dandiset.identifier}/draft/').data

    assert not resp['locked']
    assert resp['locked_by'] is None
