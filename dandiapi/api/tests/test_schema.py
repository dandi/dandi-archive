from __future__ import annotations

from dandischema.models import Asset, CommonModel, Dandiset, PublishedAsset, PublishedDandiset
from dandischema.utils import TransitionalGenerateJsonSchema
from django.conf import settings
import pytest


@pytest.mark.parametrize(
    ('model', 'version'),
    [
        (Dandiset, None),
        (Asset, None),
        (Dandiset, settings.DANDI_SCHEMA_VERSION),
        (PublishedDandiset, None),
        (PublishedAsset, None),
        (PublishedDandiset, settings.DANDI_SCHEMA_VERSION),
    ],
)
def test_schema_latest(api_client, model: CommonModel, version: str | None):
    """Test that the schema endpoints return valid schemas."""
    resp = api_client.get(
        '/api/schema/',
        {
            'verison': version or '',
            'model': model.__name__,
        },
    )
    assert resp.status_code == 200

    # Verify that the schema is json and has core properties
    schema = resp.json()
    assert isinstance(schema, dict)
    assert 'properties' in schema
    assert 'title' in schema

    # Compare with expected schema from pydantic using same generator as dandischema
    expected_schema = model.model_json_schema(schema_generator=TransitionalGenerateJsonSchema)
    assert schema == expected_schema


def test_schema_invalid_version(api_client):
    """Test that schema endpoints with invalid versions return 404."""
    resp = api_client.get('/api/schema/', {'version': 'invalid-version'})
    assert resp.status_code == 400
