from __future__ import annotations

from dandischema.models import PublishedAsset, PublishedDandiset
from django.conf import settings
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from pydantic import TypeAdapter
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound


@swagger_auto_schema(
    method='GET',
    operation_summary='Get schema for Dandiset',
    operation_description='Returns the JSONSchema for Dandiset metadata',
)
@api_view(['GET'])
def dandiset_schema_view(request, version: str | None = None):
    """
    Return the JSONSchema for Dandiset metadata.

    This endpoint provides the currently configured schema based on the application's
    DANDI_SCHEMA_VERSION setting. It can be used as a replacement for the static
    schema files hosted on GitHub.

    If a version is provided and does not match the current version, a 404 is returned.
    In the future, multiple versions could be supported.
    """
    if version and version not in {settings.DANDI_SCHEMA_VERSION, 'latest'}:
        raise NotFound(f'Schema version {version} not found')

    # Generate the schema JSON directly from the Pydantic model using TypeAdapter
    adapter = TypeAdapter(PublishedDandiset)
    schema = adapter.json_schema()

    return JsonResponse(schema)


@swagger_auto_schema(
    method='GET',
    operation_summary='Get schema for Asset',
    operation_description='Returns the JSONSchema for Asset metadata',
)
@api_view(['GET'])
def asset_schema_view(request, version: str | None = None):
    """
    Return the JSONSchema for Asset metadata.

    This endpoint provides the currently configured schema based on the application's
    DANDI_SCHEMA_VERSION setting. It can be used as a replacement for the static
    schema files hosted on GitHub.

    If a version is provided and does not match the current version, a 404 is returned.
    In the future, multiple versions could be supported.
    """
    if version and version not in {settings.DANDI_SCHEMA_VERSION, 'latest'}:
        raise NotFound(f'Schema version {version} not found')

    # Generate the schema JSON directly from the Pydantic model using TypeAdapter
    adapter = TypeAdapter(PublishedAsset)
    schema = adapter.json_schema()

    return JsonResponse(schema)
