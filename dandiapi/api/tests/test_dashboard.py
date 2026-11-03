from __future__ import annotations

import pytest

from dandiapi.api.tests.factories import UserFactory


@pytest.mark.parametrize(
    ('is_staff', 'is_superuser'),
    [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ],
)
@pytest.mark.django_db
def test_dashboard_access(api_client, is_staff, is_superuser):
    user = UserFactory.create(is_staff=is_staff, is_superuser=is_superuser)
    api_client.force_login(user)
    resp = api_client.get('/dashboard/')

    should_pass = is_staff or is_superuser
    assert resp.status_code == (200 if should_pass else 403)


@pytest.mark.django_db
def test_dashboard_access_unauthenticated(api_client):
    resp = api_client.get('/dashboard/')
    assert resp.status_code == 302


@pytest.mark.parametrize(
    ('is_staff', 'is_superuser'),
    [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ],
)
@pytest.mark.django_db
def test_user_approval_access(api_client, is_staff, is_superuser):
    user = UserFactory.create(is_staff=is_staff, is_superuser=is_superuser)
    api_client.force_login(user)

    other_user = UserFactory.create()
    resp = api_client.get(f'/dashboard/user/{other_user.username}/')

    should_pass = is_staff or is_superuser
    assert resp.status_code == (200 if should_pass else 403)


@pytest.mark.django_db
def test_user_approval_access_unauthenticated(api_client):
    other_user = UserFactory.create()
    resp = api_client.get(f'/dashboard/user/{other_user.username}/')
    assert resp.status_code == 302


@pytest.mark.parametrize(
    ('is_staff', 'is_superuser'),
    [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ],
)
@pytest.mark.django_db
def test_mailchimp_view_access(api_client, is_staff, is_superuser):
    user = UserFactory.create(is_staff=is_staff, is_superuser=is_superuser)
    api_client.force_login(user)

    resp = api_client.get('/dashboard/mailchimp/')

    should_pass = is_staff or is_superuser
    assert resp.status_code == (200 if should_pass else 403)


@pytest.mark.django_db
def test_mailchimp_view_access_unauthenticated(api_client):
    resp = api_client.get('/dashboard/mailchimp/')
    assert resp.status_code == 403
