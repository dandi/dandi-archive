import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db()
def test_search_rest(api_client: APIClient, user_factory) -> None:
    api_client.force_authenticate(user=user_factory())
    resp = api_client.get('/api/dandisets/search/')
    assert resp.status_code == 200
