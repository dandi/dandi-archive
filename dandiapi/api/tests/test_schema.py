from __future__ import annotations

from dandischema.models import Asset, CommonModel, Dandiset, PublishedAsset, PublishedDandiset
from dandischema.utils import TransitionalGenerateJsonSchema
import pytest


@pytest.mark.parametrize(
    'model',
    [
        Dandiset,
        Asset,
        PublishedDandiset,
        PublishedAsset,
    ],
)
def test_schema_latest(api_client, model: CommonModel):
    """Test that the schema endpoints return valid schemas."""
    resp = api_client.get('/api/schema/', {'model': model.__name__})
    assert resp.status_code == 200

    # Verify that the schema is json and has core properties
    schema = resp.json()
    assert isinstance(schema, dict)
    assert 'properties' in schema
    assert 'title' in schema

    # Compare with expected schema from pydantic using same generator as dandischema
    expected_schema = model.model_json_schema(schema_generator=TransitionalGenerateJsonSchema)
    assert schema == expected_schema
