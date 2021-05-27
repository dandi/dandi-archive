from allauth.account.signals import user_signed_up
from django.contrib.auth.models import User
import pytest


def serialize_social_account(social_account):
    return {
        'username': social_account.extra_data['login'],
        'name': social_account.extra_data['name'],
        'admin': social_account.user.is_superuser,
    }


@pytest.mark.django_db
def test_user_registration_email(social_account, mailoutbox):
    user = social_account.user

    # The sign up signal is only sent when the user registers through an API call.
    # This is hard to emulate, so we just send the signal manually.
    user_signed_up.send(sender=User, user=user)

    assert len(mailoutbox) == 1

    email = mailoutbox[0]
    assert email.subject == f'DANDI: New user registered: {user.email}'
    assert email.to == ['dandi@mit.edu', user.email]
    assert '<p>' not in email.body
    assert all(len(_) < 100 for _ in email.body.splitlines())


@pytest.mark.django_db
def test_user_me(api_client, social_account):
    api_client.force_authenticate(user=social_account.user)

    assert (
        api_client.get(
            '/api/users/me/',
            format='json',
        ).data
        == serialize_social_account(social_account)
    )


@pytest.mark.django_db
def test_user_me_admin(api_client, admin_user, social_account_factory):
    api_client.force_authenticate(user=admin_user)
    social_account = social_account_factory(user=admin_user)

    assert (
        api_client.get(
            '/api/users/me/',
            format='json',
        ).data
        == serialize_social_account(social_account)
    )


@pytest.mark.django_db
def test_user_search(api_client, social_account, social_account_factory):
    api_client.force_authenticate(user=social_account.user)

    # Create more users to be filtered out
    social_account_factory()
    social_account_factory()
    social_account_factory()

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': social_account.user.username},
            format='json',
        ).data
        == [serialize_social_account(social_account)]
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
def test_user_search_multiple_matches(api_client, user, user_factory, social_account_factory):
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
    social_accounts = [social_account_factory(user=user) for user in users]

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': 'jane'},
            format='json',
        ).data
        == [serialize_social_account(social_account) for social_account in social_accounts[:3]]
    )


@pytest.mark.django_db
def test_user_search_limit_enforced(api_client, user, user_factory, social_account_factory):
    api_client.force_authenticate(user=user)

    usernames = [f'jane_{i:02}' for i in range(0, 20)]
    users = [user_factory(username=username) for username in usernames]
    social_accounts = [social_account_factory(user=user) for user in users]

    assert (
        api_client.get(
            '/api/users/search/?',
            {'username': 'jane'},
            format='json',
        ).data
        == [serialize_social_account(social_account) for social_account in social_accounts[:10]]
    )
