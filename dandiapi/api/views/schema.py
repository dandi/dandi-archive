from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dandischema.models import PublishedAsset, PublishedDandiset
from dandischema.utils import TransitionalGenerateJsonSchema
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound

if TYPE_CHECKING:
    from pydantic import BaseModel


def generate_model_schema(model_class: type[BaseModel]) -> dict[str, Any]:
    """
    Generate JSON schema for a Pydantic model using the same approach as dandischema.

    This function mirrors the schema generation logic used in
    dandischema.metadata.publish_model_schemata to ensure consistency
    with the static schemas that were previously generated.

    Args:
        model_class: Pydantic model class to generate schema for

    Returns:
        dict: JSON schema for the model
    """
    return model_class.model_json_schema(schema_generator=TransitionalGenerateJsonSchema)


@swagger_auto_schema(
    method='GET',
    operation_summary='Get schema for Dandiset',
    operation_description='Returns the JSONSchema for Dandiset metadata',
)
@api_view(['GET'])
def dandiset_schema_view(request: HttpRequest, version: str | None = None) -> JsonResponse:
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

    # Generate the schema JSON using the same approach as dandischema
    schema = generate_model_schema(PublishedDandiset)

    return JsonResponse(schema)


@swagger_auto_schema(
    method='GET',
    operation_summary='Get schema for Asset',
    operation_description='Returns the JSONSchema for Asset metadata',
)
@api_view(['GET'])
def asset_schema_view(request: HttpRequest, version: str | None = None) -> JsonResponse:
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

    # Generate the schema JSON using the same approach as dandischema
    schema = generate_model_schema(PublishedAsset)

    return JsonResponse(schema)
