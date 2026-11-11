from __future__ import annotations

from django.conf import settings
from django.urls import reverse
import pytest


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_logout_clears_session_and_redirects_to_web_app(client, user_factory):
    """Visiting the allauth logout URL ends the API session and returns to the web app."""
    client.force_login(user_factory.create())
    assert '_auth_user_id' in client.session

    # The web app navigates the browser here, so it must work via GET with no confirmation page.
    response = client.get(reverse('account_logout'))

    assert response.status_code == 302
    assert response['Location'] == settings.DANDI_WEB_APP_URL
    assert '_auth_user_id' not in client.session
