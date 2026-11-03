from __future__ import annotations

from dandischema.models import Asset, CommonModel, Dandiset, PublishedAsset, PublishedDandiset
from dandischema.utils import TransitionalGenerateJsonSchema
import pytest

# Model names are listed explicitly, since `PublishedDandiset` and `PublishedAsset` are
# (deprecated) aliases of `Dandiset` and `Asset` as of dandischema 0.13.0, and thus share
# their `__name__`.
SCHEMA_MODELS = [
    ('Dandiset', Dandiset),
    ('Asset', Asset),
    ('PublishedDandiset', PublishedDandiset),
    ('PublishedAsset', PublishedAsset),
]


@pytest.mark.parametrize(('model_name', 'model'), SCHEMA_MODELS)
@pytest.mark.django_db
def test_schema_latest(api_client, model_name: str, model: CommonModel):
    """Test that the schema endpoints return valid schemas."""
    resp = api_client.get('/api/schemas/', {'model': model_name})
    assert resp.status_code == 200

    # Verify that the schema is json and has core properties
    schema = resp.json()
    assert isinstance(schema, dict)
    assert 'properties' in schema
    assert 'title' in schema

    # Compare with expected schema from pydantic using same generator as dandischema
    expected_schema = model.model_json_schema(schema_generator=TransitionalGenerateJsonSchema)
    assert schema == expected_schema


@pytest.mark.ai_generated
@pytest.mark.django_db
def test_schema_list(api_client):
    """Test that all supported model names, including the deprecated aliases, are listed."""
    resp = api_client.get('/api/schemas/available/')
    assert resp.status_code == 200
    assert resp.json() == [name for name, _ in SCHEMA_MODELS]


@pytest.mark.django_db
def test_schema_unsupported_model(api_client):
    """Test that the schema endpoint returns an error when passed invalid choice."""
    resp = api_client.get('/api/schemas/', {'model': 'NotAValidModel'})
    assert resp.status_code == 400
