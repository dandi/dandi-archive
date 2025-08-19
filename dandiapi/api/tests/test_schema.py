from __future__ import annotations

from dandischema.models import Asset, Dandiset, PublishedAsset, PublishedDandiset
from dandischema.utils import TransitionalGenerateJsonSchema
from django.conf import settings
from django.urls import reverse
import pytest
import requests


@pytest.mark.parametrize(
    ('endpoint', 'model', 'kwargs'),
    [
        ('schema-dandiset-latest', Dandiset, {}),
        ('schema-asset-latest', Asset, {}),
        ('schema-dandiset', Dandiset, {'version': settings.DANDI_SCHEMA_VERSION}),
        ('schema-published-dandiset-latest', PublishedDandiset, {}),
        ('schema-published-asset-latest', PublishedAsset, {}),
        (
            'schema-published-dandiset',
            PublishedDandiset,
            {'version': settings.DANDI_SCHEMA_VERSION},
        ),
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

    # Compare with expected schema from pydantic using same generator as dandischema
    expected_schema = model.model_json_schema(schema_generator=TransitionalGenerateJsonSchema)
    assert schema == expected_schema


@pytest.mark.parametrize(
    'endpoint',
    [
        'schema-dandiset',
        'schema-asset',
        'schema-published-dandiset',
        'schema-published-asset',
    ],
)
def test_schema_invalid_version(api_client, endpoint):
    """Test that schema endpoints with invalid versions return 404."""
    url = reverse(endpoint, kwargs={'version': 'invalid-version'})
    resp = api_client.get(url)
    assert resp.status_code == 404
