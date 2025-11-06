from __future__ import annotations

import pytest

from dandiapi.api.tests.factories import UserFactory


@pytest.mark.django_db
def test_auth_token_retrieve(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    assert api_client.get('/api/auth/token/').data == user.auth_token.key


@pytest.mark.django_db
def test_auth_token_retrieve_unauthorized(api_client):
    assert api_client.get('/api/auth/token/').status_code == 401


@pytest.mark.django_db
def test_auth_token_refresh(api_client):
    user = UserFactory.create()
    api_client.force_authenticate(user=user)

    old_token_key = user.auth_token.key
    new_token_key = api_client.post('/api/auth/token/').data
    assert new_token_key != old_token_key

    user.auth_token.refresh_from_db()
    assert new_token_key == user.auth_token.key


@pytest.mark.django_db
def test_auth_token_reset_unauthorized(api_client):
    assert api_client.post('/api/auth/token/').status_code == 401
