from __future__ import annotations

from dandischema.models import PublishedAsset, PublishedDandiset
from dandischema.utils import TransitionalGenerateJsonSchema
from django.conf import settings
from django.urls import reverse
import pytest
import requests


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

    # Compare with expected schema from pydantic using same generator as dandischema
    expected_schema = model.model_json_schema(schema_generator=TransitionalGenerateJsonSchema)
    assert schema == expected_schema

    # Also compare against the original GitHub schema content
    schema_type = endpoint.split('-')[1]  # Extract 'dandiset' or 'asset' from endpoint name
    github_url = (
        'https://raw.githubusercontent.com/dandi/schema/master/'
        f'releases/{settings.DANDI_SCHEMA_VERSION}/{schema_type}.json'
    )

    # Download and compare with GitHub schema
    github_resp = requests.get(github_url)
    github_resp.raise_for_status()
    github_schema = github_resp.json()

    # Our local schema should match the GitHub schema
    assert schema == github_schema


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
