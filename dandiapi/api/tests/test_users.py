from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.urls.base import reverse
import pytest
from pytest_django.asserts import assertContains
from rest_framework.exceptions import ErrorDetail

from dandiapi.api.models import UserMetadata
from dandiapi.api.tests.factories import UserFactory
from dandiapi.api.views.auth import COLLECT_USER_NAME_QUESTIONS, NEW_USER_QUESTIONS, QUESTIONS

if TYPE_CHECKING:
    from django.core.mail.message import EmailMessage
    from django.test.client import Client
    from rest_framework.test import APIClient


def serialize_user(user):
    social_account = user.socialaccount_set.get()
    return {
        'username': social_account.extra_data['login'],
        'name': social_account.extra_data['name'],
        'admin': user.is_superuser,
        'status': user.metadata.status,
    }


@pytest.mark.django_db
def test_user_registration_email_content(mailoutbox: list[EmailMessage], api_client: APIClient):
    user = UserFactory.create(metadata__status=UserMetadata.Status.INCOMPLETE)  # simulates new user
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
    user = UserFactory.create(metadata__status=status)
    api_client.force_authenticate(user=user)

    api_client.post(
        '/api/users/questionnaire-form/',
        {f'question_{i}': f'answer_{i}' for i in range(len(QUESTIONS))},
    )
    assert len(mailoutbox) == email_count


@pytest.mark.django_db
def test_user_me(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    assert api_client.get('/api/users/me/').data == serialize_user(user)


@pytest.mark.django_db
def test_user_search(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    # Create more users to be filtered out
    UserFactory.create()
    UserFactory.create()
    UserFactory.create()

    assert api_client.get(
        '/api/users/search/?', {'username': user.socialaccount_set.get().extra_data['login']}
    ).data == [serialize_user(user)]


@pytest.mark.django_db
@pytest.mark.parametrize('search', ['', '_'], ids=['blank', 'missing'])
def test_user_search_none(api_client, search: str):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    assert api_client.get('/api/users/search/?', {'username': str}).data == []


@pytest.mark.django_db
def test_user_search_multiple_matches(api_client):
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
    users = [UserFactory.create(username=username) for username in usernames]

    assert api_client.get('/api/users/search/?', {'username': 'odysseus'}).data == [
        serialize_user(user) for user in users[:3]
    ]


@pytest.mark.django_db
def test_user_search_limit_enforced(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    usernames = [f'odysseus_{i:02}' for i in range(20)]
    users = [UserFactory.create(username=username) for username in usernames]

    assert api_client.get('/api/users/search/?', {'username': 'odysseus'}).json() == [
        serialize_user(user) for user in users[:10]
    ]


@pytest.mark.django_db
def test_user_search_extra_data(api_client):
    """Test that searched keyword isn't caught by a different field in `extra_data`."""
    user = UserFactory.create(social_account__extra_data__test='odysseus')
    api_client.force_authenticate(user=user)

    assert api_client.get('/api/users/search/?', {'username': 'odysseus'}).data == []


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
    user = UserFactory.create(
        first_name='John',
        last_name='Doe',
        username='john.doe@dandi.test',
        metadata__status=status,
    )
    api_client.force_authenticate(user=user)

    # test that only APPROVED users can create dandisets
    name = 'Test Dandiset'
    metadata = {'foo': 'bar'}
    response = api_client.post('/api/dandisets/', {'name': name, 'metadata': metadata})
    assert response.status_code == expected_status_code

    # test that only APPROVED users show up in search
    response = api_client.get('/api/users/search/?', {'username': user.username})
    resp_data = response.data
    assert resp_data == expected_search_results_value


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('questions', 'expected_status_code'),
    [
        (NEW_USER_QUESTIONS, 200),
        (COLLECT_USER_NAME_QUESTIONS, 200),
        ([], 404),
    ],
)
def test_user_questionnaire_view(
    admin_client: Client,
    questions: list[dict[str, Any]],
    expected_status_code: int,
):
    query_params = {'QUESTIONS': json.dumps(questions)} if questions else None
    resp = admin_client.get(reverse('user-questionnaire'), query_params=query_params)

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
    user = UserFactory.create(email=email, metadata__status=UserMetadata.Status.INCOMPLETE)
    api_client.force_authenticate(user=user)

    resp = api_client.post(reverse('user-questionnaire'))
    assert resp.status_code == 302
    assert user.metadata.status == expected_status


@pytest.mark.django_db
def test_user_list_requires_admin(api_client: APIClient):
    resp = api_client.get('/api/users/')
    assert resp.status_code == 401

    normal_user = UserFactory.create()
    api_client.force_authenticate(user=normal_user)
    resp = api_client.get('/api/users/')
    assert resp.status_code == 403

    staff_user = UserFactory.create(is_staff=True)
    api_client.force_authenticate(user=staff_user)
    resp = api_client.get('/api/users/')
    assert resp.status_code == 200

    superuser = UserFactory.create(is_superuser=True)
    api_client.force_authenticate(user=superuser)
    resp = api_client.get('/api/users/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_user_list_user_without_socialaccount(api_client: APIClient):
    # Intentionally create an approved superuser without a social account, so that we
    # can both query the endpoint, as well as see an empty result
    approved_user = UserFactory.create(is_superuser=True, social_account=None)

    # Test without filtering
    api_client.force_authenticate(user=approved_user)
    resp = api_client.get('/api/users/')
    assert resp.json() == []


@pytest.mark.django_db
def test_user_list_approved_toggle(api_client: APIClient):
    approved_user = UserFactory.create(is_superuser=True)
    UserFactory.create(metadata__status=UserMetadata.Status.PENDING)
    UserFactory.create(metadata__status=UserMetadata.Status.INCOMPLETE)
    UserFactory.create(metadata__status=UserMetadata.Status.REJECTED)

    # Test without filtering
    api_client.force_authenticate(user=approved_user)
    resp = api_client.get('/api/users/')
    assert len(resp.json()) == 4

    resp = api_client.get('/api/users/', {'approved_only': True})
    assert resp.json() == [approved_user.socialaccount_set.get().extra_data['login']]
