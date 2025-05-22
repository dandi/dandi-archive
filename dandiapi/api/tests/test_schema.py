from __future__ import annotations

from dandischema.models import PublishedAsset, PublishedDandiset
from django.conf import settings
from django.urls import reverse
from pydantic import TypeAdapter
import pytest


@pytest.mark.parametrize(
    ('endpoint', 'model', 'kwargs'),
    [
        ('schema-dandiset-latest', PublishedDandiset, {}),
        ('schema-asset-latest', PublishedAsset, {}),
        ('schema-dandiset', PublishedDandiset, {'version': settings.DANDI_SCHEMA_VERSION}),
    ],
)
def test_schema_latest(api_client, endpoint, model, kwargs):
    """Test that the schema endpoints return valid schemas."""
    url = reverse(endpoint, kwargs=kwargs)
    resp = api_client.get(url)
    assert resp.status_code == 200

    # Verify that the schema is json and has core properties
    schema = resp.json()
    assert isinstance(schema, dict)
    assert 'properties' in schema
    assert 'title' in schema

    # Compare with expected schema from pydantic
    adapter = TypeAdapter(model)
    expected_schema = adapter.json_schema()
    assert schema == expected_schema


@pytest.mark.parametrize(
    'endpoint',
    [
        'schema-dandiset',
        'schema-asset',
    ],
)
def test_schema_invalid_version(api_client, endpoint):
    """Test that schema endpoints with invalid versions return 404."""
    url = reverse(endpoint, kwargs={'version': 'invalid-version'})
    resp = api_client.get(url)
    assert resp.status_code == 404
