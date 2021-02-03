import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from .factories import (
    AssetBlobFactory,
    AssetFactory,
    AssetMetadataFactory,
    DandisetFactory,
    DraftVersionFactory,
    PublishedVersionFactory,
    UserFactory,
    ValidationFactory,
    VersionMetadataFactory,
)

register(AssetFactory)
register(AssetBlobFactory)
register(AssetMetadataFactory)
register(DandisetFactory)
register(PublishedVersionFactory)
register(DraftVersionFactory)
# registering DraftVersionFactory after PublishedVersionFactory means
# the fixture `version` will always be a draft
register(UserFactory)
register(ValidationFactory)
register(VersionMetadataFactory)


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authenticated_api_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client
