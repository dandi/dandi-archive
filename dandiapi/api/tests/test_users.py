import pytest


def serialize(user):
    return {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'admin': user.is_superuser,
    }


@pytest.mark.django_db
def test_user_me(api_client, user):
    api_client.force_authenticate(user=user)

    assert (
        api_client.get(
            '/api/users/me/',
            format='json',
        ).data
        == serialize(user)
    )


@pytest.mark.django_db
def test_user_me_admin(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)

    assert (
        api_client.get(
            '/api/users/me/',
            format='json',
        ).data
        == serialize(admin_user)
    )


@pytest.mark.django_db
def test_user_search(api_client, user, user_factory):
    api_client.force_authenticate(user=user)

    # Create more users to be filtered out
    user_factory()
    user_factory()
    user_factory()

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': user.username},
            format='json',
        ).data
        == [serialize(user)]
    )


@pytest.mark.django_db
def test_user_search_blank_username(api_client, user):
    api_client.force_authenticate(user=user)

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': ''},
            format='json',
        ).data
        == {'username': ['This field may not be blank.']}
    )


@pytest.mark.django_db
def test_user_search_no_matches(api_client, user):
    api_client.force_authenticate(user=user)

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': '_'},
            format='json',
        ).data
        == []
    )


@pytest.mark.django_db
def test_user_search_multiple_matches(api_client, user, user_factory):
    api_client.force_authenticate(user=user)

    usernames = [
        'jane_bar',
        'jane_doe',
        'jane_foo',
        # Some extra users to be filtered out
        'john_bar',
        'john_doe',
        'john_foo',
    ]
    users = [user_factory(username=username) for username in usernames]

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': 'jane'},
            format='json',
        ).data
        == [serialize(user) for user in users[:3]]
    )


@pytest.mark.django_db
def test_user_search_alphabetical(api_client, user, user_factory):
    api_client.force_authenticate(user=user)

    # Create the users in reverse alphabetical order
    user_z = user_factory(username='jane_z')
    user_a = user_factory(username='jane_a')

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': 'jane'},
            format='json',
        ).data
        == [serialize(user_a), serialize(user_z)]
    )


@pytest.mark.django_db
def test_user_search_limit_enforced(api_client, user, user_factory):
    api_client.force_authenticate(user=user)

    usernames = [f'jane_{i:02}' for i in range(0, 100)]
    users = [user_factory(username=username) for username in usernames]

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': 'jane'},
            format='json',
        ).data
        == [serialize(user) for user in users[:10]]
    )
