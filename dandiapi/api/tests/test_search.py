from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from rest_framework.test import APIClient


@pytest.mark.django_db()
def test_search_rest(api_client: APIClient) -> None:
    resp = api_client.get('/api/dandisets/search/')
    assert resp.status_code == 200
