from __future__ import annotations

from django.urls import reverse
from oauth2_provider import urls as oauth2_urls
from oauth2_provider.models import Application
import pytest

from dandiapi.api.tests.factories import UserFactory
from dandiapi.urls import oauth2_urlpatterns

ADMIN_ACCESS_PARAMS = pytest.mark.parametrize(
    ('is_staff', 'is_superuser'),
    [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ],
)


def test_oauth_urlpatterns_match_toolkit():
    """The toolkit's routes are all mounted, only with different views for some of them."""
    assert {(str(url.pattern), url.name) for url in oauth2_urlpatterns} == {
        (str(url.pattern), url.name) for url in oauth2_urls.urlpatterns
    }


@pytest.mark.parametrize(
    'url_name',
    ['list', 'register'],
)
@pytest.mark.django_db
def test_oauth_application_access_unauthenticated(api_client, url_name):
    resp = api_client.get(reverse(f'oauth2_provider:{url_name}'))
    assert resp.status_code == 302


@pytest.mark.parametrize(
    'url_name',
    ['list', 'register'],
)
@ADMIN_ACCESS_PARAMS
@pytest.mark.django_db
def test_oauth_application_access(api_client, url_name, is_staff, is_superuser):
    user = UserFactory.create(is_staff=is_staff, is_superuser=is_superuser)
    api_client.force_login(user)
    resp = api_client.get(reverse(f'oauth2_provider:{url_name}'))

    should_pass = is_staff or is_superuser
    assert resp.status_code == (200 if should_pass else 403)


@pytest.mark.parametrize(
    'url_name',
    ['detail', 'update', 'delete'],
)
@ADMIN_ACCESS_PARAMS
@pytest.mark.django_db
def test_oauth_application_detail_access(api_client, url_name, is_staff, is_superuser):
    user = UserFactory.create(is_staff=is_staff, is_superuser=is_superuser)
    application = Application.objects.create(
        user=user,
        name='Test application',
        client_type=Application.CLIENT_PUBLIC,
        authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
        redirect_uris='https://example.com/callback',
    )
    api_client.force_login(user)
    resp = api_client.get(reverse(f'oauth2_provider:{url_name}', args=[application.pk]))

    should_pass = is_staff or is_superuser
    assert resp.status_code == (200 if should_pass else 403)


@ADMIN_ACCESS_PARAMS
@pytest.mark.django_db
def test_oauth_application_register(api_client, is_staff, is_superuser):
    user = UserFactory.create(is_staff=is_staff, is_superuser=is_superuser)
    api_client.force_login(user)
    resp = api_client.post(
        reverse('oauth2_provider:register'),
        {
            'name': 'Test application',
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret',
            'client_type': Application.CLIENT_PUBLIC,
            'authorization_grant_type': Application.GRANT_AUTHORIZATION_CODE,
            'redirect_uris': 'https://example.com/callback',
        },
        format='multipart',
    )

    if is_staff or is_superuser:
        application = Application.objects.get(client_id='test-client-id')
        assert application.user == user
        assert resp.status_code == 302
        assert resp.url == reverse('oauth2_provider:detail', args=[application.pk])
    else:
        assert resp.status_code == 403
        assert not Application.objects.filter(client_id='test-client-id').exists()


@pytest.mark.django_db
def test_oauth_authorized_tokens_access(api_client):
    """Non-admin users can still manage the tokens they have authorized."""
    user = UserFactory.create()
    api_client.force_login(user)
    resp = api_client.get(reverse('oauth2_provider:authorized-token-list'))
    assert resp.status_code == 200
