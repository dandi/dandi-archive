from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.urls.base import reverse
import pytest
from pytest_django.asserts import assertContains
from rest_framework.exceptions import ErrorDetail

from dandiapi.api.models import UserMetadata
from dandiapi.api.tests.factories import SocialAccountFactory, UserFactory
from dandiapi.api.views.auth import COLLECT_USER_NAME_QUESTIONS, NEW_USER_QUESTIONS, QUESTIONS
from dandiapi.api.views.users import user_to_dict

if TYPE_CHECKING:
    from django.core.mail.message import EmailMessage
    from django.test.client import Client
    from rest_framework.response import Response
    from rest_framework.test import APIClient


def serialize_social_account(social_account):
    return {
        'username': social_account.extra_data['login'],
        'name': social_account.extra_data['name'],
        'admin': social_account.user.is_superuser,
        'status': social_account.user.metadata.status,
    }


@pytest.mark.django_db
def test_user_registration_email_content(mailoutbox: list[EmailMessage], api_client: APIClient):
    social_account = SocialAccountFactory.create()
    user = social_account.user
    social_account.user.metadata.status = UserMetadata.Status.INCOMPLETE  # simulates new user

    api_client.force_authenticate(user=user)
    api_client.post(
        '/api/users/questionnaire-form/',
        {f'question_{i}': f'answer_{i}' for i in range(len(QUESTIONS))},
    )

    assert len(mailoutbox) == 2

    email = mailoutbox[0]
    assert email.subject == f'DANDI: New user registered: {user.email}'
    assert email.to == [settings.DANDI_ADMIN_EMAIL, user.email]
    assert '<p>' not in email.body
    assert all(len(_) < 100 for _ in email.body.splitlines())

    email = mailoutbox[1]
    assert email.subject == f'DANDI: Review new user: {user.username}'
    assert email.to == [settings.DANDI_ADMIN_EMAIL]
    assert '<p>' not in email.body
    assert all(len(_) < 100 for _ in email.body.splitlines())


@pytest.mark.parametrize(
    ('status', 'email_count'),
    [
        # INCOMPLETE users POSTing to the questionnaire endpoint should result in 2 emails
        # being sent (new user welcome email, admin "needs approval" email), while no email should
        # be sent in the case of APPROVED/PENDING users
        (UserMetadata.Status.INCOMPLETE, 2),
        (UserMetadata.Status.PENDING, 0),
        (UserMetadata.Status.APPROVED, 0),
    ],
)
@pytest.mark.django_db
def test_user_registration_email_count(
    mailoutbox: list[EmailMessage],
    api_client: APIClient,
    status: str,
    email_count: int,
):
    social_account = SocialAccountFactory.create()
    user = social_account.user
    user.metadata.status = status
    api_client.force_authenticate(user=user)
    api_client.post(
        '/api/users/questionnaire-form/',
        {f'question_{i}': f'answer_{i}' for i in range(len(QUESTIONS))},
    )
    assert len(mailoutbox) == email_count


@pytest.mark.django_db
def test_user_me(api_client):
    social_account = SocialAccountFactory.create()
    api_client.force_authenticate(user=social_account.user)

    assert api_client.get('/api/users/me/').data == serialize_social_account(social_account)


@pytest.mark.django_db
def test_user_me_admin(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    social_account = SocialAccountFactory.create(user=admin_user)
    UserMetadata.objects.create(user=admin_user)

    assert api_client.get('/api/users/me/').data == serialize_social_account(social_account)


@pytest.mark.django_db
def test_user_search(api_client):
    social_account = SocialAccountFactory.create()
    api_client.force_authenticate(user=social_account.user)

    # Create more users to be filtered out
    SocialAccountFactory.create()
    SocialAccountFactory.create()
    SocialAccountFactory.create()

    assert api_client.get(
        '/api/users/search/?', {'username': social_account.user.username}
    ).data == [serialize_social_account(social_account)]


@pytest.mark.django_db
def test_user_search_prefer_social(api_client, user_factory):
    social_account = SocialAccountFactory.create()
    api_client.force_authenticate(user=social_account.user)

    # Check that when social account is present, it is used
    assert api_client.get(
        '/api/users/search/?', {'username': social_account.user.username}
    ).data == [serialize_social_account(social_account)]

    # Create user without a social account
    user = user_factory()
    api_client.force_authenticate(user=user)
    assert api_client.get('/api/users/search/?', {'username': user.username}).data == [
        user_to_dict(user)
    ]


@pytest.mark.django_db
def test_user_search_blank_username(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    assert api_client.get('/api/users/search/?', {'username': ''}).data == []


@pytest.mark.django_db
def test_user_search_no_matches(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    assert api_client.get('/api/users/search/?', {'username': '_'}).data == []


@pytest.mark.django_db
def test_user_search_multiple_matches(api_client, user_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    usernames = [
        'odysseus_bar',
        'odysseus_doe',
        'odysseus_foo',
        # Some extra users to be filtered out
        'john_bar',
        'john_doe',
        'john_foo',
    ]
    users = [user_factory(username=username) for username in usernames]
    social_accounts = [SocialAccountFactory.create(user=user) for user in users]

    assert api_client.get('/api/users/search/?', {'username': 'odysseus'}).data == [
        serialize_social_account(social_account) for social_account in social_accounts[:3]
    ]


@pytest.mark.django_db
def test_user_search_limit_enforced(api_client, user_factory):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    usernames = [f'odysseus_{i:02}' for i in range(20)]
    users = [user_factory(username=username) for username in usernames]
    social_accounts = [SocialAccountFactory.create(user=user) for user in users]

    assert api_client.get('/api/users/search/?', {'username': 'odysseus'}).json() == [
        serialize_social_account(social_account) for social_account in social_accounts[:10]
    ]


@pytest.mark.django_db
def test_user_search_extra_data(api_client):
    """Test that searched keyword isn't caught by a different field in `extra_data`."""
    user = UserFactory.create()
    social_account = SocialAccountFactory.create()
    api_client.force_authenticate(user=user)

    social_accounts = [SocialAccountFactory.create() for _ in range(3)]
    social_accounts[-1].extra_data['test'] = social_account.extra_data['login']

    assert api_client.get(
        '/api/users/search/?', {'username': social_account.extra_data['login']}
    ).data == [serialize_social_account(social_account)]


@pytest.mark.parametrize(
    ('status', 'expected_status_code', 'expected_search_results_value'),
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
    status: str,
    expected_status_code: int,
    expected_search_results_value: dict,
):
    user = UserFactory.create()
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
    response: Response = api_client.post('/api/dandisets/', {'name': name, 'metadata': metadata})
    assert response.status_code == expected_status_code

    # test that only APPROVED users show up in search
    response: Response = api_client.get('/api/users/search/?', {'username': user.username})
    assert response.data == expected_search_results_value


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('questions', 'querystring', 'expected_status_code'),
    [
        (NEW_USER_QUESTIONS, f'QUESTIONS={json.dumps(NEW_USER_QUESTIONS)}', 200),
        (COLLECT_USER_NAME_QUESTIONS, f'QUESTIONS={json.dumps(NEW_USER_QUESTIONS)}', 200),
        ([], '', 404),
    ],
)
def test_user_questionnaire_view(
    admin_client: Client,
    questions: list[dict[str, Any]],
    querystring: str,
    expected_status_code: int,
):
    resp = admin_client.get(f'{reverse("user-questionnaire")}?{querystring}')
    assert resp.status_code == expected_status_code

    for question in questions:
        assertContains(resp, question['question'])


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('email', 'expected_status'),
    [
        ('test@test.com', UserMetadata.Status.PENDING),
        ('test@test.edu', UserMetadata.Status.APPROVED),
    ],
)
def test_user_edu_auto_approve(api_client: APIClient, email: str, expected_status: str):
    user = UserFactory.create()
    user.email = email
    user.save(update_fields=['email'])
    user_metadata: UserMetadata = user.metadata
    user_metadata.status = UserMetadata.Status.INCOMPLETE
    user_metadata.save(update_fields=['status'])

    api_client.force_authenticate(user=user)
    resp = api_client.post(reverse('user-questionnaire'))
    assert resp.status_code == 302

    assert user_metadata.status == expected_status


@pytest.mark.django_db
def test_user_list_requires_admin(user_factory, api_client: APIClient):
    resp = api_client.get('/api/users/')
    assert resp.status_code == 401

    normal_user = user_factory()
    api_client.force_authenticate(user=normal_user)
    resp = api_client.get('/api/users/')
    assert resp.status_code == 403

    staff_user = user_factory(is_staff=True)
    api_client.force_authenticate(user=staff_user)
    resp = api_client.get('/api/users/')
    assert resp.status_code == 200

    superuser = user_factory(is_superuser=True)
    api_client.force_authenticate(user=superuser)
    resp = api_client.get('/api/users/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_user_list_user_without_socialaccount(user_factory, api_client: APIClient):
    # Intentionally create an approved superuser without a social account, so that we
    # can both query the endpoint, as well as see an empty result
    approved_user = user_factory(is_superuser=True)

    # Test without filtering
    api_client.force_authenticate(user=approved_user)
    resp = api_client.get('/api/users/')
    assert resp.json() == []


@pytest.mark.django_db
def test_user_list_approved_toggle(api_client: APIClient):
    # Must use social_account_factory instead of user_factory, as otherwise
    # the social account won't be created on its own.
    approved_user = SocialAccountFactory.create(user__is_superuser=True).user
    SocialAccountFactory.create(user__metadata__status=UserMetadata.Status.PENDING)
    SocialAccountFactory.create(user__metadata__status=UserMetadata.Status.INCOMPLETE)
    SocialAccountFactory.create(user__metadata__status=UserMetadata.Status.REJECTED)

    # Test without filtering
    api_client.force_authenticate(user=approved_user)
    resp = api_client.get('/api/users/')
    assert len(resp.json()) == 4

    resp = api_client.get('/api/users/', {'approved_only': True})
    assert resp.json() == [approved_user.socialaccount_set.first().extra_data['login']]
