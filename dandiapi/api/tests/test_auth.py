from __future__ import annotations
import pytest
from rest_framework.authtoken.models import Token


@pytest.fixture()
def token(user) -> Token:
    return Token.objects.get(user=user)


@pytest.mark.django_db()
def test_auth_token_retrieve(api_client, user, token):
    api_client.force_authenticate(user=user)

    assert api_client.get('/api/auth/token/').data == token.key


@pytest.mark.django_db()
def test_auth_token_retrieve_unauthorized(api_client, user, token):
    assert api_client.get('/api/auth/token/').status_code == 401


@pytest.mark.django_db()
def test_auth_token_refresh(api_client, user, token):
    api_client.force_authenticate(user=user)

    new_token_key = api_client.post('/api/auth/token/').data
    assert new_token_key != token.key

    new_token = Token.objects.get(user=user)
    assert new_token_key == new_token.key


@pytest.mark.django_db()
def test_auth_token_reset_unauthorized(api_client, user, token):
    assert api_client.post('/api/auth/token/').status_code == 401
