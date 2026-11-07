from __future__ import annotations

from django.urls import reverse
import pytest


@pytest.mark.django_db
@pytest.mark.parametrize(
    'path',
    [
        '/api/info/',
        '/api/schemas/available/',
        '/api/does-not-exist/',
    ],
)
def test_api_responses_noindex(api_client, path):
    response = api_client.get(path)
    assert response['X-Robots-Tag'] == 'noindex'


@pytest.mark.django_db
def test_robots_txt_not_noindex(api_client):
    response = api_client.get(reverse('robots_txt'))
    assert 'X-Robots-Tag' not in response
