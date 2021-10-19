from django.contrib.auth.models import User
import pytest
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response
from rest_framework.test import APIClient

from dandiapi.api.models import UserMetadata
from dandiapi.api.views.users import QUESTIONS


def serialize_social_account(social_account):
    return {
        'username': social_account.extra_data['login'],
        'name': social_account.extra_data['name'],
        'admin': social_account.user.is_superuser,
        'status': social_account.user.metadata.status,
    }


@pytest.mark.django_db
def test_user_registration_email(social_account, mailoutbox, api_client):
    user = social_account.user
    api_client.force_authenticate(user=user)
    api_client.post(
        '/api/users/questionnaire-form/',
        {question: f'answer_{i}' for i, question in enumerate(QUESTIONS)},
        format='json',
    )

    assert len(mailoutbox) == 2

    email = mailoutbox[0]
    assert email.subject == f'DANDI: New user registered: {user.email}'
    assert email.to == ['dandi@mit.edu', user.email]
    assert '<p>' not in email.body
    assert all(len(_) < 100 for _ in email.body.splitlines())

    email = mailoutbox[1]
    assert email.subject == f'DANDI: New user registration to review: {user.username}'
    assert email.to == ['dandi@mit.edu']
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
    UserMetadata.objects.create(user=admin_user)

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


@pytest.mark.parametrize(
    'status,expected_status_code,expected_search_results_value',
    [
        (
            UserMetadata.Status.APPROVED,
            200,
            [
                {
                    'admin': False,
                    'username': 'john.doe@dandi.test',
                    'name': 'John Doe',
                    'status': UserMetadata.Status.APPROVED,
                }
            ],
        ),
        (
            UserMetadata.Status.PENDING,
            403,
            {
                'detail': ErrorDetail(
                    string='You do not have permission to perform this action.',
                    code='permission_denied',
                )
            },
        ),
        (
            UserMetadata.Status.INCOMPLETE,
            403,
            {
                'detail': ErrorDetail(
                    string='You do not have permission to perform this action.',
                    code='permission_denied',
                )
            },
        ),
        (
            UserMetadata.Status.REJECTED,
            403,
            {
                'detail': ErrorDetail(
                    string='You do not have permission to perform this action.',
                    code='permission_denied',
                )
            },
        ),
    ],
)
@pytest.mark.django_db
def test_user_status(
    api_client: APIClient,
    user: User,
    status: str,
    expected_status_code: int,
    expected_search_results_value: dict,
):
    user_metadata: UserMetadata = user.metadata
    user_metadata.status = status
    user_metadata.save()

    user.first_name = 'John'
    user.last_name = 'Doe'
    user.username = 'john.doe@dandi.test'
    user.save()
    api_client.force_authenticate(user=user)

    # test that only APPROVED users can create dandisets
    name = 'Test Dandiset'
    metadata = {'foo': 'bar'}
    response: Response = api_client.post(
        '/api/dandisets/', {'name': name, 'metadata': metadata}, format='json'
    )
    assert response.status_code == expected_status_code

    # test that only APPROVED users show up in search
    response: Response = api_client.get(
        '/api/users/search/?', {'username': user.username}, format='json'
    )
    assert response.data == expected_search_results_value
