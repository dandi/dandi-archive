from __future__ import annotations

from dandischema.models import PublishedAsset, PublishedDandiset
from django.conf import settings
from django.urls import reverse
from pydantic import TypeAdapter


def test_dandiset_schema_latest(api_client):
    """Test that the schema endpoint returns a valid schema for Dandiset."""
    url = reverse('schema-dandiset-latest')
    resp = api_client.get(url)
    assert resp.status_code == 200

    # Verify that the schema is json and has core properties
    schema = resp.json()
    assert isinstance(schema, dict)
    assert 'properties' in schema
    assert 'title' in schema

    # Compare with expected schema from pydantic
    adapter = TypeAdapter(PublishedDandiset)
    expected_schema = adapter.json_schema()
    assert schema == expected_schema


def test_asset_schema_latest(api_client):
    """Test that the schema endpoint returns a valid schema for Asset."""
    url = reverse('schema-asset-latest')
    resp = api_client.get(url)
    assert resp.status_code == 200

    # Verify that the schema is json and has core properties
    schema = resp.json()
    assert isinstance(schema, dict)
    assert 'properties' in schema
    assert 'title' in schema

    # Compare with expected schema from pydantic
    adapter = TypeAdapter(PublishedAsset)
    expected_schema = adapter.json_schema()
    assert schema == expected_schema


def test_dandiset_schema_versioned(api_client):
    """Test that the schema endpoint with version returns a valid schema for Dandiset."""
    url = reverse('schema-dandiset', kwargs={'version': settings.DANDI_SCHEMA_VERSION})
    resp = api_client.get(url)
    assert resp.status_code == 200

    # Verify that the schema is json and has core properties
    schema = resp.json()
    assert isinstance(schema, dict)
    assert 'properties' in schema
    assert 'title' in schema

    # Compare with expected schema from pydantic
    adapter = TypeAdapter(PublishedDandiset)
    expected_schema = adapter.json_schema()
    assert schema == expected_schema


def test_dandiset_schema_invalid_version(api_client):
    """Test that the schema endpoint with invalid version returns 404."""
    url = reverse('schema-dandiset', kwargs={'version': 'invalid-version'})
    resp = api_client.get(url)
    assert resp.status_code == 404


def test_asset_schema_invalid_version(api_client):
    """Test that the schema endpoint with invalid version returns 404."""
    url = reverse('schema-asset', kwargs={'version': 'invalid-version'})
    resp = api_client.get(url)
    assert resp.status_code == 404
