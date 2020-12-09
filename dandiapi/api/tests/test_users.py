import pytest


@pytest.mark.django_db
def test_user_search(api_client, user_factory):

    user = user_factory()
    # Create more users to filter out
    user_factory()
    user_factory()
    user_factory()

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': user.username},
            format='json',
        ).data
        == [{'username': user.username}]
    )


@pytest.mark.django_db
def test_user_search_blank_username(api_client, user):

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

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': '_'},
            format='json',
        ).data
        == []
    )


@pytest.mark.django_db
def test_user_search_multiple_matches(api_client, user_factory):

    usernames = [
        'jane_doe',
        'jane_foo',
        'jane_bar',
        'john_doe',
        'john_foo',
        'john_bar',
    ]
    for username in usernames:
        user_factory(username=username)

    expected_usernames = usernames[:3]
    expected_usernames.sort()

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': 'jane'},
            format='json',
        ).data
        == [{'username': username} for username in expected_usernames]
    )


@pytest.mark.django_db
def test_user_search_limit_enforced(api_client, user_factory):

    usernames = [f'jane_{i:02}' for i in range(0, 100)]
    for username in usernames:
        user_factory(username=username)

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': 'jane'},
            format='json',
        ).data
        == [{'username': username} for username in usernames[:10]]
    )
