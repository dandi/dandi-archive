from random import randint

from django.contrib.auth.models import User
from django.test.client import Client
from django.urls import reverse
import pytest
from pytest_django.asserts import assertContains, assertNotContains

from dandiapi.api.models import UserMetadata


@pytest.mark.django_db
def test_users_dashboard(client: Client, admin_client: Client, user, user_factory):
    for status, _ in UserMetadata.Status.choices:
        for _ in range(randint(0, 10)):
            user = user_factory()
            user.metadata.status = status
            user.metadata.save()

    for status, _ in UserMetadata.Status.choices:
        page_url = f'{reverse("dashboard-users")}?metadata__status={status}'

        # Non-admin users should be redirected to a login page
        assert client.get(page_url).status_code == 302

        resp = admin_client.get(page_url)

        assert resp.status_code == 200

        assertContains(
            resp,
            f'There are currently {User.objects.filter(metadata__status=status).count()}'
            f' {status} users',
        )

        for user in User.objects.filter(metadata__status=status):
            assertContains(resp, user.email)
            assertContains(resp, user.first_name)
            assertContains(resp, user.last_name)
            assertNotContains(resp, 'AnonymousUser')
