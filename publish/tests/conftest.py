import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from .factories import AssetFactory, DandisetFactory, UserFactory, VersionFactory


register(AssetFactory)
register(DandisetFactory)
register(UserFactory)
register(VersionFactory)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()
